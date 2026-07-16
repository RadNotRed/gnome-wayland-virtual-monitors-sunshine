from __future__ import annotations

import ast
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]


class UninstallScriptTests(unittest.TestCase):
    def run_uninstaller(
        self,
        *,
        current_features: str,
        marker: bool = False,
        legacy_snapshot: str | None = None,
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            state_dir = (
                home
                / ".local/state/gnome-wayland-virtual-monitors-sunshine"
            )
            state_dir.mkdir(parents=True)
            if marker:
                (state_dir / "added-scale-monitor-framebuffer").touch()
            if legacy_snapshot is not None:
                (state_dir / "original-experimental-features").write_text(
                    legacy_snapshot,
                    encoding="utf-8",
                )

            feature_state = root / "features"
            feature_state.write_text(current_features, encoding="utf-8")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            self.write_executable(
                fake_bin / "systemctl",
                "#!/usr/bin/env bash\nexit 0\n",
            )
            self.write_executable(
                fake_bin / "gsettings",
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import os
                    import sys
                    from pathlib import Path

                    state = Path(os.environ["GSETTINGS_STATE"])
                    if sys.argv[1] == "get":
                        print(state.read_text(encoding="utf-8").strip())
                    elif sys.argv[1] == "set":
                        state.write_text(sys.argv[-1], encoding="utf-8")
                    else:
                        raise SystemExit(2)
                    """
                ),
            )

            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "GSETTINGS_STATE": str(feature_state),
                    "PATH": f"{fake_bin}:{environment['PATH']}",
                }
            )
            subprocess.run(
                ["bash", "scripts/uninstall-user.sh"],
                cwd=REPOSITORY,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            return ast.literal_eval(feature_state.read_text(encoding="utf-8"))

    @staticmethod
    def write_executable(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def test_removes_only_the_feature_added_by_the_installer(self):
        features = self.run_uninstaller(
            current_features="['scale-monitor-framebuffer', 'unrelated-feature']",
            marker=True,
        )
        self.assertEqual(features, ["unrelated-feature"])

    def test_preserves_feature_that_predated_a_legacy_install(self):
        features = self.run_uninstaller(
            current_features="['scale-monitor-framebuffer', 'unrelated-feature']",
            legacy_snapshot="['scale-monitor-framebuffer']",
        )
        self.assertEqual(
            features,
            ["scale-monitor-framebuffer", "unrelated-feature"],
        )
