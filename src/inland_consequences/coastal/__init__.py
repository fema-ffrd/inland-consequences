"""Meta distribution entry for coastal.

This package exists so the distribution has a canonical import name
(`coastal`) while the bundled `sphere` package is placed under
`src/sphere/` and will be included in the wheel.
"""

def main() -> None:
    print("Hello from coastal meta package")