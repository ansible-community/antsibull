# SPDX-License-Identifier: Python-2.0.1
# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007,
# 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019,
# 2020, 2021, 2022, 2023 Python Software Foundation; All Rights Reserved

"""
Modifed code derived from Cpython's `shutil` module to suit our own needs
"""

from __future__ import annotations

import os
import typing as t
from pathlib import Path
from shutil import Error, copy2, copystat

if t.TYPE_CHECKING:
    from _typeshed import StrPath


def copytree_and_symlinks(
    src: StrPath | os.DirEntry,
    dest: StrPath | os.DirEntry,
    *,
    ignore_dangling_symlinks: bool = True,
    dirs_exist_ok: bool = False,
    _origsrc: Path | None = None,
) -> None:
    """
    Modified version of `shutil.copytree()` that handles symlinks more inteligently.

    * Relative symlink to files within the `src` directory -> symlink is preserved
    * Relative symlink to files outside the `src` directory -> files are copied
    * `ignore_dangling_symlinks` is the default.

    Windows code branches are removed. Antsibull does not support Windows.
    """
    # Ensure that the generator is closed
    with os.scandir(src) as itr:  # type: ignore[type-var]
        entries = list(itr)
    _copytree(
        entries,
        src,
        dest,
        ignore_dangling_symlinks=ignore_dangling_symlinks,
        dirs_exist_ok=dirs_exist_ok,
        _origsrc=_origsrc,
    )


def _should_symlink(src: Path, target: Path, origsrc: Path) -> bool:
    """
    Check if `src`'s symlink target is a path outside `src` that cannot be
    symlinked

    Args:
        src:
            Source directory
        target:
            Symlink target
    """
    if target.is_absolute():
        return True
    try:
        srcr = src.resolve()
        targetr = (srcr / target).resolve()
        if not targetr.is_dir():
            targetr = targetr.parent
        is_relative = origsrc.is_relative_to(targetr)
        return origsrc == targetr or not is_relative
    except Exception:  # pragma: no cover pylint: disable=broad-exception-caught
        return False


def _copytree(  # noqa: C901
    entries: list[os.DirEntry],
    src: StrPath,
    dst: StrPath,
    ignore_dangling_symlinks: bool,
    dirs_exist_ok: bool = False,
    *,
    _origsrc: Path | None = None,
) -> None:
    copy_function = copy2
    _origsrc = _origsrc if _origsrc else Path(src).resolve()

    os.makedirs(dst, exist_ok=dirs_exist_ok)
    errors = []

    for srcentry in entries:
        srcname = os.path.join(src, srcentry.name)
        dstname = os.path.join(dst, srcentry.name)
        srcobj = srcentry
        try:
            is_symlink = srcentry.is_symlink()
            if is_symlink:
                linkto = os.readlink(srcname)
                if _should_symlink(Path(src), Path(linkto), _origsrc):
                    # We can't just leave it to `copy_function` because legacy
                    # code with a custom `copy_function` may rely on copytree
                    # doing the right thing.
                    os.symlink(linkto, dstname)
                    copystat(srcobj, dstname, follow_symlinks=False)
                else:
                    # ignore dangling symlink if the flag is on
                    if (
                        not os.path.exists(os.path.join(src, linkto))
                        and ignore_dangling_symlinks
                    ):
                        continue
                    if srcentry.is_dir():
                        copytree_and_symlinks(
                            srcobj,
                            dstname,
                            ignore_dangling_symlinks=ignore_dangling_symlinks,
                            dirs_exist_ok=dirs_exist_ok,
                            _origsrc=_origsrc,
                        )
                    else:
                        copy_function(srcobj, dstname)
            elif srcentry.is_dir():
                copytree_and_symlinks(
                    srcobj,
                    dstname,
                    ignore_dangling_symlinks=ignore_dangling_symlinks,
                    dirs_exist_ok=dirs_exist_ok,
                    _origsrc=_origsrc,
                )
            else:
                # Will raise a SpecialFileError for unsupported file types
                copy_function(srcobj, dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])
        except OSError as why:
            errors.append((srcname, dstname, str(why)))
    copystat(src, dst)
    if errors:
        raise Error(errors)


__all__ = ("copytree_and_symlinks",)
