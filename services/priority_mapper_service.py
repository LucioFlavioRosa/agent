class PriorityMapperService:
    @staticmethod
    def map_moscow_to_azure_priority(moscow_value: str) -> int:
        if not moscow_value:
            return 2
        value = moscow_value.strip().lower()
        moscow_map = {
            'm': 1,
            'must': 1,
            's': 2,
            'should': 2,
            'c': 3,
            'could': 3,
            "w": 4,
            "won't": 4,
            "wont": 4
        }
        return moscow_map.get(value, 2)
