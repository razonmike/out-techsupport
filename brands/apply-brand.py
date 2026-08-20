#!/usr/bin/env python3
"""
apply-brand.py <brand.toml> [--tree <path>]

Prepares a RustDesk source tree for a specific brand:
  - replaces "RustDesk" brand strings in src/lang/*.rs with the display name
  - sets powered_by_me per locale
  - patches Cargo.toml ProductName / FileDescription
  - patches flutter/windows/runner/Runner.rc
  - copies the brand icon over res/icon.ico + flutter app_icon.ico
The server/key/password/APP_NAME come from OTS_* env vars at *compile* time
(see load_custom_client / config.rs), so this script only touches
display-level assets. Emits an env file to source before `cargo`/`build.py`.
"""
import sys, os, re, shutil, tomllib, pathlib

def load(path):
    with open(path, "rb") as f:
        return tomllib.load(f)

def main():
    if len(sys.argv) < 2:
        print("usage: apply-brand.py <brand.toml> [--tree <path>]"); sys.exit(1)
    manifest = load(sys.argv[1])
    tree = "."
    if "--tree" in sys.argv:
        tree = sys.argv[sys.argv.index("--tree")+1]
    tree = pathlib.Path(tree).resolve()
    ident = manifest["identity"]; srv = manifest["server"]; sec = manifest["secrets"]
    disp = ident["display_name"]
    about = manifest.get("about", {})

    # 1) brand strings in lang files: RustDesk -> display_name
    lang_dir = tree/"src"/"lang"
    n=0
    for f in lang_dir.glob("*.rs"):
        t=f.read_text(encoding="utf-8")
        orig=t
        # powered_by_me per locale
        if f.name=="ru.rs":
            t=re.sub(r'\("powered_by_me", "[^"]*"\)', f'("powered_by_me", "{ident["powered_by_ru"]}")', t)
        else:
            t=re.sub(r'\("powered_by_me", "[^"]*"\)', f'("powered_by_me", "{ident["powered_by_en"]}")', t)
        # About-card slogan (blue banner) per locale
        if about:
            slogan = about["slogan_ru"] if f.name=="ru.rs" else about["slogan_en"]
            t=re.sub(r'\("Slogan_tip", "[^"]*"\)', f'("Slogan_tip", "{slogan}")', t)
        # generic RustDesk -> display name inside quoted strings only
        t=t.replace("RustDesk", disp)
        if t!=orig:
            f.write_text(t,encoding="utf-8",newline=""); n+=1
    print(f"lang files branded: {n}")

    # 1b) About-card copyright (blue banner): drop "Purslane Tech Pte. Ltd." +
    # license, keep the "Copyright © YEAR " prefix, append the brand holder.
    if about:
        sp = tree/"flutter"/"lib"/"desktop"/"pages"/"desktop_setting_page.dart"
        s = sp.read_text(encoding="utf-8")
        s2 = s.replace(r'Purslane Tech Pte. Ltd.\n$license', about["copyright"])
        if s2 != s:
            sp.write_text(s2, encoding="utf-8", newline="")
            print(f"about copyright -> {about['copyright']}")
        else:
            print("WARN: about copyright anchor not found")

    # 2) Cargo.toml product metadata
    cargo=tree/"Cargo.toml"
    c=cargo.read_text(encoding="utf-8")
    c=re.sub(r'ProductName\s*=\s*"[^"]*"', f'ProductName = "{ident["product_name"]}"', c)
    c=re.sub(r'FileDescription\s*=\s*"[^"]*"', f'FileDescription = "{ident["file_desc"]}"', c)
    cargo.write_text(c,encoding="utf-8",newline="")
    print("Cargo.toml metadata set")

    # 3) Runner.rc
    rc=tree/"flutter"/"windows"/"runner"/"Runner.rc"
    if rc.exists():
        r=rc.read_text(encoding="utf-8",errors="ignore")
        r=re.sub(r'VALUE "FileDescription", "[^"]*"', f'VALUE "FileDescription", "{ident["file_desc"]}"', r)
        r=re.sub(r'VALUE "ProductName", "[^"]*"', f'VALUE "ProductName", "{ident["product_name"]}"', r)
        rc.write_text(r,encoding="utf-8",newline="")
        print("Runner.rc set")

    # 4) icon
    icon_src=(pathlib.Path(sys.argv[1]).parent/ident.get("app_name","")).parent
    icon_rel=manifest["assets"]["icon_ico"]
    icon_path=(pathlib.Path(sys.argv[1]).parent/icon_rel).resolve()
    if icon_path.exists():
        for dst in [tree/"res"/"icon.ico",
                    tree/"flutter"/"windows"/"runner"/"resources"/"app_icon.ico"]:
            if dst.parent.exists():
                shutil.copy(icon_path, dst); print(f"icon -> {dst}")
    else:
        print(f"WARN: icon not found: {icon_path}")

    # 4b) home-screen logo (per brand). *.png is gitignored, so it is NOT
    # committed under flutter/assets — apply-brand stages it at build time.
    # A brand with no logo_png ships without a logo (loadLogo -> Offstage)
    # rather than borrowing another brand's logo.
    logo_dst = tree/"flutter"/"assets"/"logo.png"
    logo_rel = manifest["assets"].get("logo_png")
    if logo_rel:
        logo_path=(pathlib.Path(sys.argv[1]).parent/logo_rel).resolve()
        if logo_path.exists():
            shutil.copy(logo_path, logo_dst); print(f"logo -> {logo_dst}")
        else:
            print(f"WARN: logo not found: {logo_path}")
    elif logo_dst.exists():
        logo_dst.unlink(); print("logo removed (brand has no logo_png)")
    else:
        print("no logo_png for this brand")

    # 4c) logo box height (per brand). Square logos (Onix) look tiny in the
    # default 60px slot sized for a wide wordmark (TechSupport); let a brand
    # raise the slot height so a square mark renders larger.
    lh = manifest["assets"].get("logo_max_height", 60)
    if lh != 60:
        cp = tree/"flutter"/"lib"/"common.dart"
        c = cp.read_text(encoding="utf-8")
        c2 = c.replace("BoxConstraints(maxWidth: 300, maxHeight: 60)",
                       f"BoxConstraints(maxWidth: 300, maxHeight: {lh})")
        if c2 != c:
            cp.write_text(c2, encoding="utf-8", newline="")
            print(f"logo box maxHeight -> {lh}")
        else:
            print("WARN: logo constraint anchor not found")

    # 4d) in-window corner icon (loadIcon -> assets/icon.png). apply-brand
    # replaces it per brand so the titlebar corner matches the brand mark.
    #    (loadIcon tries icon.png first, so the png always wins over icon.svg.)
    icon_png_rel = manifest["assets"].get("icon_png")
    if icon_png_rel:
        icon_png_src = (pathlib.Path(sys.argv[1]).parent/icon_png_rel).resolve()
        icon_png_dst = tree/"flutter"/"assets"/"icon.png"
        if icon_png_src.exists():
            shutil.copy(icon_png_src, icon_png_dst); print(f"corner icon -> {icon_png_dst}")
        else:
            print(f"WARN: icon_png not found: {icon_png_src}")

    # 5) compile-time env file
    #    agent_hook: install-time Tailscale+AgentSSH setup, opt-in per brand.
    agent_hook = bool(manifest.get("hooks", {}).get("agent_hook", False))
    envf=tree/".brand-env"
    env_lines = [
        f'export OTS_APP_NAME="{ident["app_name"]}"',
        f'export OTS_RENDEZVOUS="{srv["rendezvous"]}"',
        f'export OTS_API_SERVER="{srv["api"]}"',
        f'export OTS_SERVER_KEY="{srv["key"]}"',
        f'export OTS_CLIENT_PASSWORD="{sec["password"]}"',
    ]
    if agent_hook:
        env_lines.append('export OTS_AGENT_HOOK="1"')
    envf.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    print(f"agent_hook: {'on' if agent_hook else 'off'}")
    print(f"env written: {envf}")
    print("=== brand applied:", disp, "===")

if __name__=="__main__":
    main()
