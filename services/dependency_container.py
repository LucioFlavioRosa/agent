from tools.epic_markdown_parser import EpicMarkdownParser
class DependencyContainer:
    def __init__(self):
        self._epic_parser = None
        # ... outros atributos ...
    def get_epic_parser(self):
        if self._epic_parser is None:
            self._epic_parser = EpicMarkdownParser()
        return self._epic_parser
    # ... demais métodos inalterados ...