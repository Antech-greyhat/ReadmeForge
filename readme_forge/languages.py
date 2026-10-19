"""Language badge metadata: Simple Icons slug, badge colour and logo colour."""

from __future__ import annotations

import re
from typing import NamedTuple


class LangMeta(NamedTuple):
    slug: str | None
    color: str
    logo_color: str | None = None


# Keys are normalised with norm_lang so "Jupyter Notebook" and "jupyter-notebook" match.
LANG_META: dict[str, LangMeta] = {
    "javascript": LangMeta("javascript", "F7DF1E", "black"),
    "typescript": LangMeta("typescript", "3178C6"),
    "python": LangMeta("python", "3776AB"),
    "java": LangMeta("openjdk", "ED8B00", "black"),
    "c": LangMeta("c", "A8B9CC", "black"),
    "c++": LangMeta("cplusplus", "00599C"),
    "c#": LangMeta("csharp", "239120"),
    "f#": LangMeta("fsharp", "378BBA"),
    "go": LangMeta("go", "00ADD8"),
    "rust": LangMeta("rust", "000000"),
    "ruby": LangMeta("ruby", "CC342D"),
    "php": LangMeta("php", "777BB4"),
    "swift": LangMeta("swift", "F05138"),
    "kotlin": LangMeta("kotlin", "7F52FF"),
    "dart": LangMeta("dart", "0175C2"),
    "scala": LangMeta("scala", "DC322F"),
    "elixir": LangMeta("elixir", "4B275F"),
    "haskell": LangMeta("haskell", "5D4F85"),
    "lua": LangMeta("lua", "2C2D72"),
    "r": LangMeta("r", "276DC3"),
    "julia": LangMeta("julia", "9558B2"),
    "perl": LangMeta("perl", "39457E"),
    "zig": LangMeta("zig", "F7A41D", "black"),
    "html": LangMeta("html5", "E34F26"),
    "css": LangMeta("css3", "1572B6"),
    "scss": LangMeta("sass", "CC6699"),
    "sass": LangMeta("sass", "CC6699"),
    "less": LangMeta("less", "1D365D"),
    "shell": LangMeta("gnubash", "4EAA25"),
    "bash": LangMeta("gnubash", "4EAA25"),
    "powershell": LangMeta("powershell", "5391FE"),
    "dockerfile": LangMeta("docker", "2496ED"),
    "docker": LangMeta("docker", "2496ED"),
    "cmake": LangMeta("cmake", "064F8C"),
    "jupyternotebook": LangMeta("jupyter", "F37626"),
    "jupyter": LangMeta("jupyter", "F37626"),
    "vue": LangMeta("vuedotjs", "4FC08D"),
    "vuejs": LangMeta("vuedotjs", "4FC08D"),
    "svelte": LangMeta("svelte", "FF3E00"),
    "astro": LangMeta("astro", "BC52EE"),
    "vimscript": LangMeta("vim", "019733"),
    "vim": LangMeta("vim", "019733"),
    "emacslisp": LangMeta("gnuemacs", "7F5AB6"),
    "clojure": LangMeta("clojure", "5881D8"),
    "erlang": LangMeta("erlang", "A90533"),
    "ocaml": LangMeta("ocaml", "EC6813"),
    "solidity": LangMeta("solidity", "363636"),
    "nix": LangMeta("nixos", "5277C3"),
    "hcl": LangMeta("terraform", "7B42BC"),
    "terraform": LangMeta("terraform", "7B42BC"),
    "plpgsql": LangMeta("postgresql", "4169E1"),
    "postgresql": LangMeta("postgresql", "4169E1"),
    "tsql": LangMeta("microsoftsqlserver", "CC2927"),
    "groovy": LangMeta("apachegroovy", "4298B8"),
    "markdown": LangMeta("markdown", "000000"),
    "mdx": LangMeta("mdx", "1B1F24"),
    "tex": LangMeta("latex", "008080"),
    "latex": LangMeta("latex", "008080"),
    "blade": LangMeta("laravel", "FF2D20"),
    "handlebars": LangMeta("handlebarsdotjs", "000000"),
}

LANG_FALLBACK = LangMeta(None, "05122A")


def norm_lang(name: object) -> str:
    return re.sub(r"[\s._-]", "", str(name or "").lower())


def lang_meta(name: str) -> LangMeta:
    return LANG_META.get(norm_lang(name), LANG_FALLBACK)
