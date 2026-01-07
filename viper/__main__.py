"""Entry point for Viper Terminal."""

from viper.app import ViperApp


def main() -> None:
    """Launch the Viper Terminal application."""
    app = ViperApp()
    app.run()


if __name__ == "__main__":
    main()
