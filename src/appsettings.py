class AppSettings:
    """Настройки приложения json"""

    def __init__(
            self,
            is_debug: bool = False,
            fields: str = '',
            max_row_count: int = 0,
            is_use_filter: str = '',
            is_only_unique: bool = False
    ):
        self.as_isdebug = is_debug
        self.as_fields = fields
        self.as_max_row_count = max_row_count
        self.as_is_use_filter = is_use_filter
        self.as_is_only_unique = is_only_unique
