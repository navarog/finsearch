import React, { useRef } from "react";
import { TextField } from "@mui/material";
import "./EmojiTextField.scss";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";


export const ALLOWED_EMOJIS = [
    "DrawCard",
    "FishEgg",
    "FishHatch",
    "YoungFish",
    "SchoolFeederMove",
    "SchoolFish",
    "FishFromHand",
    "ConsumeFish",
    "Discard",
    "AllPlayers",
    "ArrowDown",
    "Estuary",
    "FishLengthSmall",
    "FishLengthMedium",
    "FishLengthLarge",
    "FlipperBlue",
    "FlipperGreen",
    "FlipperPurple",
    "PlayFishBottomRow",
    "Predator",
    "Wave",
]

const EmojiTextField = ({ query, setQuery, ...props }) => {
    const textFieldRef = useRef(null);

    const renderText = (text) => {
        const emojiRegex = /\[([^\]]+)\]/g;
        const parts = text.split(emojiRegex);

        return parts.map((part, index) => {
            if (index % 2 === 0) {
                return part;
            }

            return (
                <span
                    key={index}
                    className="emoji-marker"
                    contentEditable={false}
                >
                    <img
                        src={require(`../assets/icons/${part}.svg`)}
                        alt={part}
                    />
                    <span>{part}</span>
                </span>
            );
        });
    };

    const filterInvalidEmoji = (text) => {
        const emojiRegex = /\[([^\]]+)\]/g;
        return text.replace(emojiRegex, (match, emoji) => {
            return ALLOWED_EMOJIS.includes(emoji) ? match : "";
        });
    }

    const handleChange = (e) => {
        e.target.value = filterInvalidEmoji(e.target.value);
        setQuery({ ...query, text: e.target.value });
    };

    const handleKeyDown = (e) => {
        if (e.key === "Backspace") {
            const input = e.target;
            const cursorPosition = input.selectionStart;
            const textBeforeCursor = query.text.slice(0, cursorPosition);
            const emojiMatch = textBeforeCursor.match(/\[[^\]]+\]$/);

            if (emojiMatch) {
                e.preventDefault();
                const newValue =
                    query.text.slice(0, cursorPosition - emojiMatch[0].length) +
                    query.text.slice(cursorPosition);

                setQuery({ ...query, text: newValue });

                setTimeout(() => {
                    const newPosition = cursorPosition - emojiMatch[0].length;
                    input.selectionStart = newPosition;
                    input.selectionEnd = newPosition;
                }, 0);
            }
        }
    };

    return (
        <div className="emoji-textfield-container">
            <TextField
                {...props}
                inputRef={textFieldRef}
                variant="standard"
                value={query.text}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                className="search-input"
                autoComplete="off"
                sx={{
                    "& .MuiInputBase-input": {
                        position: "relative",
                        zIndex: 1
                    },
                    width: "100%"
                }}
                InputProps={{
                    endAdornment: query.text && (
                        <InputAdornment position="end">
                            <IconButton
                                onClick={() => setQuery({ ...query, text: "" })}
                                edge="end"
                                size="small"
                            >
                                <CloseIcon />
                            </IconButton>
                        </InputAdornment>
                    ),
                }}
            />
            <div className="rendered-content">
                {renderText(query.text)}
            </div>
        </div>
    );
};

export default EmojiTextField;