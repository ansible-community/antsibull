#!/usr/bin/env python3
import argparse
import yaml


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--depsfile",
        help="Path to an ansible.deps file",
        required=True
    )
    args = parser.parse_args()
    return args


def main():
    args = get_args()

    with open(args.depsfile) as f:
        deps = f.readlines()
    deps = [x.strip() for x in deps]

    galaxy_reqs = []
    for dep in deps:
        if not dep.startswith("#") and not dep.startswith("_"):
            collection, version = dep.split(":")
            galaxy_reqs.append(dict(
                name=collection,
                version=version.strip(),
                source="https://galaxy.ansible.com"
            ))

    print(yaml.dump({"collections": galaxy_reqs}, default_flow_style=False))


if __name__ == "__main__":
    main()
