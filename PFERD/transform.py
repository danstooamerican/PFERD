"""
Transforms let the user define functions to decide where the downloaded files
should be placed locally. They let the user do more advanced things like moving
only files whose names match a regex, or renaming files from one numbering
scheme to another.
"""

from dataclasses import dataclass
from pathlib import PurePath
from typing import Callable, List, Optional, TypeVar

from .utils import PathLike, Regex, to_path, to_pattern

Transform = Callable[[PurePath], Optional[PurePath]]


@dataclass
class Transformable:
    """
    An object that can be transformed by a Transform.
    """

    path: PurePath


TF = TypeVar("TF", bound=Transformable)


def apply_transform(
        transform: Transform,
        transformables: List[TF],
) -> List[TF]:
    """
    Apply a Transform to multiple Transformables, discarding those that were
    not transformed by the Transform.
    """

    result: List[TF] = []

    for transformable in transformables:
        new_path = transform(transformable.path)

        if new_path:
            transformable.path = new_path
            result.append(transformable)

    return result


# Transform combinators

keep = lambda path: path


def attempt(*args: Transform) -> Transform:
    def apply_transforms_until_first_success(path: PurePath) -> Optional[PurePath]:
        for transform in args:
            result = transform(path)

            if result:
                return result

        return None

    return apply_transforms_until_first_success


def optionally(transform: Transform) -> Transform:
    return attempt(transform, lambda path: path)


def do(*args: Transform) -> Transform:
    def apply_transforms_if_all_succeed(path: PurePath) -> Optional[PurePath]:
        current_result = path

        for transform in args:
            result = transform(current_result)

            if result:
                current_result = result
            else:
                return None

        return current_result

    return apply_transforms_if_all_succeed


def predicate(pred: Callable[[PurePath], bool]) -> Transform:
    def apply_predicate(path: PurePath) -> Optional[PurePath]:
        if pred(path):
            return path

        return None

    return apply_predicate


def glob(pattern: str) -> Transform:
    return predicate(lambda path: path.match(pattern))


def move_dir(source_dir: PathLike, target_dir: PathLike) -> Transform:
    source_path = to_path(source_dir)
    target_path = to_path(target_dir)

    def make_child_of_target_dir(path: PurePath) -> Optional[PurePath]:
        if source_path in path.parents:
            return target_path / path.relative_to(source_path)

        return None

    return make_child_of_target_dir


def move(source: PathLike, target: PathLike) -> Transform:
    source_path = to_path(source)
    target_path = to_path(target)

    def move_to_target(path: PurePath) -> Optional[PurePath]:
        if path == source_path:
            return target_path

        return None

    return move_to_target


def rename(source: str, target: str) -> Transform:
    def rename_to_target_name(path: PurePath) -> Optional[PurePath]:
        if path.name == source:
            return path.with_name(target)

        return None

    return rename_to_target_name


def re_move(regex: Regex, target: str) -> Transform:
    def move_if_match(path: PurePath) -> Optional[PurePath]:
        match = to_pattern(regex).fullmatch(str(path))

        if match:
            groups = [match.group(0)]
            groups.extend(match.groups())

            return PurePath(target.format(*groups))

        return None

    return move_if_match


def re_rename(regex: Regex, target: str) -> Transform:
    def rename_if_match(path: PurePath) -> Optional[PurePath]:
        match = to_pattern(regex).fullmatch(path.name)

        if match:
            groups = [match.group(0)]
            groups.extend(match.groups())

            return path.with_name(target.format(*groups))

        return None

    return rename_if_match
