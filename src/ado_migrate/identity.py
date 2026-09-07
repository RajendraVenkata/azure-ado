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
        """One line per distinct identity actually referenced during this
        run (deduplicated), for the migration report's "Users" section."""
        return [
            f"{source} -> {destination}"
            if destination != UNMAPPED_PLACEHOLDER
            else f"{source} -> UNMAPPED (no destination identity configured)"
            for source, destination in sorted(self.resolved.items())
        ]


def load_identity_map(path: str) -> IdentityMap:
    with open(path) as f:
        raw = yaml.safe_load(f)

    return IdentityMap(raw.get("mappings", {}))
