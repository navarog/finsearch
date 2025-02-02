###
# Convert all png/jpg assets to webp
###

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

find ${SCRIPT_DIR}/../src/assets/ -type f \( -iname "*.jpg" -o -iname "*.png" \) | while read -r file
do
    webp_file="${file%.*}.webp"
    if [ ! -f "$webp_file" ]; then
        cwebp -q 25 -m 6 "$file" -o "$webp_file"
    fi
done

