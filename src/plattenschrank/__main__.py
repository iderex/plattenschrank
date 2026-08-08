"""Allow ``python -m plattenschrank`` to reach the same entry point."""

from plattenschrank.cli import main

raise SystemExit(main())
