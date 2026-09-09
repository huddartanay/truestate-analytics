"""Validated, versioned static entity configuration; never imports dashboards."""
from __future__ import annotations
import json
import re
from pathlib import Path
from types import MappingProxyType

from intelligence import config as cfg
from intelligence.enums import Emirate, EntityType
from intelligence.errors import EntityRegistryError
from intelligence.schemas import EntityDefinition
from intelligence.entities.normalize import normalize

SPECIFIC = frozenset(e for e in Emirate if e not in (Emirate.UNKNOWN,Emirate.UAE_WIDE,Emirate.MULTI_EMIRATE))
PARENTS = {
    EntityType.COUNTRY:set(), EntityType.EMIRATE:{EntityType.COUNTRY}, EntityType.CITY:{EntityType.EMIRATE},
    EntityType.AREA:{EntityType.EMIRATE,EntityType.CITY},
    EntityType.COMMUNITY:{EntityType.EMIRATE,EntityType.CITY,EntityType.AREA},
    EntityType.PROJECT:{EntityType.EMIRATE,EntityType.CITY,EntityType.AREA,EntityType.COMMUNITY},
    EntityType.BUILDING:{EntityType.EMIRATE,EntityType.CITY,EntityType.AREA,EntityType.COMMUNITY,EntityType.PROJECT},
    EntityType.DEVELOPER:set(),
}


class Registry:
    def __init__(self, definitions, version):
        if not isinstance(version,str) or not version.strip() or len(version)>64:
            raise EntityRegistryError('Invalid entity registry version')
        try:
            definitions=tuple(EntityDefinition.model_validate(d) for d in definitions)
        except ValueError as exc:
            raise EntityRegistryError('Invalid canonical entity definition') from exc
        entities={e.entity_id:e for e in definitions}
        if len(entities)!=len(definitions):raise EntityRegistryError('Duplicate canonical entity ID')
        aliases={}
        for entity in definitions:
            kind=entity.entity_type
            if not entity.entity_id.startswith(kind.value.lower()+':'):
                raise EntityRegistryError('Entity ID prefix must match its type')
            if kind in (EntityType.COUNTRY,EntityType.DEVELOPER):
                if entity.parent_entity_id or entity.emirate is not None:
                    raise EntityRegistryError('Country/developer cannot have a geographic parent or emirate')
            else:
                if entity.emirate not in SPECIFIC or not entity.parent_entity_id:
                    raise EntityRegistryError('Geographic entity requires a specific emirate and explicit parent')
                parent=entities.get(entity.parent_entity_id)
                if parent is None or parent.entity_type not in PARENTS[kind]:
                    raise EntityRegistryError('Invalid entity parent type or missing parent')
                if kind==EntityType.EMIRATE:
                    if entity.entity_id!='emirate:'+entity.emirate.value.lower():
                        raise EntityRegistryError('Emirate identity must match declared scope')
                elif parent.emirate != entity.emirate:
                    raise EntityRegistryError('Cross-emirate hierarchy conflict')
                if entity.active and not parent.active:raise EntityRegistryError('Active child requires active parent')
            seen={entity.entity_id};parent_id=entity.parent_entity_id
            while parent_id:
                if parent_id in seen:raise EntityRegistryError('Cyclic entity hierarchy')
                seen.add(parent_id)
                if parent_id not in entities:raise EntityRegistryError('Unknown ancestor')
                parent_id=entities[parent_id].parent_entity_id
            for alias in entity.aliases:
                value=normalize(alias.text)
                if not value or len(value)>160:raise EntityRegistryError('Empty or overlong normalized alias')
                if alias.abbreviation and (kind!=EntityType.EMIRATE or alias.text not in ('RAK','UAQ')):
                    raise EntityRegistryError('Only approved geographic abbreviations are supported')
                if value in aliases and aliases[value][0].entity_id != entity.entity_id:
                    raise EntityRegistryError('Conflicting alias identities or types')
                if value in aliases and aliases[value][1].abbreviation!=alias.abbreviation:
                    raise EntityRegistryError('Alias matching policy conflict')
                aliases[value]=(entity,alias)
        self.version=version
        self.entities=MappingProxyType(entities)
        self.matchers=tuple((value,entity,alias,re.compile(r'(?<!\w)'+re.escape(value)+r'(?!\w)'))
                            for value,(entity,alias) in sorted(aliases.items()) if entity.active)


def load_registry(path=None):
    try:
        data=json.loads(Path(path or Path(__file__).with_name('catalog.json')).read_text())
        if data['version']!=cfg.ENTITY_REGISTRY_VERSION:
            raise EntityRegistryError('Configured registry version does not match static catalog')
        return Registry(data['entities'],data['version'])
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise EntityRegistryError('Cannot load entity registry') from exc


REGISTRY=load_registry()
