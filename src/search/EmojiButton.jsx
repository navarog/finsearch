import React from "react";


const EmojiButton = ({ query, setQuery, icon }) => {
    return <img src={require(`../assets/icons/${icon}.svg`)} alt={icon} onClick={() => setQuery({ ...query, text: query.text + `[${icon}]` })}></img>
}

export default EmojiButton