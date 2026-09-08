import yaml

UNMAPPED_PLACEHOLDER = "unmapped-owner"


class IdentityMap:
    def __init__(self, mappings: dict[str, str]):
        self._mappings = mappings
        self.unmapped_identities: list[str] = []
        self.resolved: dict[str, str] = {}

    def resolve(self, source_identity: str) -> str:
        if source_identity in self._mappings:
            destination = self._mappings[source_identity]
            self.resolved[source_identity] = destination
            return destination

        self.unmapped_identities.append(source_identity)
        self.resolved[source_identity] = UNMAPPED_PLACEHOLDER
        return UNMAPPED_PLACEHOLDER

    def report_items(self) -> list[str]:
        """One line per distinct identity resolved so far (deduplicated)."""
        return [
            format_resolution(source, destination)
            for source, destination in sorted(self.resolved.items())
        ]


def format_resolution(source: str, destination: str) -> str:
    if destination == UNMAPPED_PLACEHOLDER:
        return f"{source} -> UNMAPPED (no destination identity configured)"
    return f"{source} -> {destination}"


def load_identity_map(path: str) -> IdentityMap:
    with open(path) as f:
        raw = yaml.safe_load(f)

    return IdentityMap(raw.get("mappings", {}))
