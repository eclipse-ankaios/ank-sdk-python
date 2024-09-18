from ankaios_sdk import Ankaios, AnkaiosLogLevel


if __name__ == "__main__":
    ank = Ankaios()
    ank.set_logger_level(AnkaiosLogLevel.INFO)

    ank.start_read()
    ank.write_to_control_interface()
    ank.join_read()

    exit(0)
