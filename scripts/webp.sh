###
# Convert all png/jpg assets to webp
###

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

find ${SCRIPT_DIR}/../src/assets/ -type f \( -iname "*.jpg" -o -iname "*.png" \) | while read -r file
do
    cwebp -q 25 -m 6 "$file" -o "${file%.*}.webp"
done

