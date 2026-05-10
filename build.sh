#!/usr/bin/env bash

TARGET=mydic.tar.gz
ANDROID_TARGET=mydic.apk

cd "$(dirname "$0")"

rm -rf build/target

# Project common
mkdir -p build/target && \
rsync -ar --files-from=.deploy . build/target &&
mv build/target/compose.yaml.prod build/target/compose.yaml || exit 1

cp -r scripts systemd build/target || exit 1

# Backend
mkdir -p build/target/backend && \
rsync -ar --files-from=backend/.deploy --exclude-from=backend/.deployignore backend build/target/backend || exit 1

# Frontend
mkdir -p build/target/frontend && \
npm run build --prefix frontend && \
cp -r frontend/dist/* build/target/frontend || exit 1

# Android app
#mkdir -p build/target/android && \
#cp android/app/build/outputs/apk/release/${ANDROID_TARGET} "build/target/android/${ANDROID_TARGET}" &&
#cp android/VERSION.txt build/target/android || exit 1

# Target package
tar --owner=root --group=root -czf "build/${TARGET}" -C build/target . || exit 1

echo "Built successfully: ${TARGET}"
