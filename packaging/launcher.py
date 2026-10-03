"""PyInstaller entry point (a plain script; the package itself uses relative imports)."""
import multiprocessing

from neurosync.ui.app import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
