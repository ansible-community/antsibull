#!/bin/bash

SASSC=${SASS_COMPILER:-$(which sassc)}
POSTCSS=${POSTCSS:-$(which postcss)}

if [ "${SASSC}" == "" ]; then
    echo "Need 'sassc' on path. You can install sassc with 'apt-get install sassc'."
    exit -1
fi

if [ "${POSTCSS}" == "" ]; then
    echo "Need 'postcss' on path. You can install postcss and the required plugins with 'npm install autoprefixer cssnano postcss postcss-cli'."
    exit -1
fi

export BROWSERSLIST_CONFIG=browserslistrc

set -e

build_css() {
    SOURCE="$1.scss"
    DEST="../$1.css"
    set -x
    ${SASSC} "${SOURCE}" "${DEST}"
    ${POSTCSS} --use autoprefixer --use cssnano --no-map -r "${DEST}"
    { set +x; } 2>/dev/null  # https://stackoverflow.com/a/19226038
}

build_css antsibull-minimal
