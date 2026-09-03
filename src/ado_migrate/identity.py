import yaml

UNMAPPED_PLACEHOLDER = "unmapped-owner"


class IdentityMap:
    def __init__(self, mappings: dict[str, str]):
        self._mappings = mappings
        self.unmapped_identities: list[str] = []

    def resolve(self, source_identity: str) -> str:
        if source_identity in self._mappings:
            return self._mappings[source_identity]

        self.unmapped_identities.append(source_identity)
        return UNMAPPED_PLACEHOLDER


def load_identity_map(path: str) -> IdentityMap:
    with open(path) as f:
        raw = yaml.safe_load(f)

    return IdentityMap(raw.get("mappings", {}))
