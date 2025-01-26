import React from "react";
import "./Card.scss";
import WaveIcon from "../assets/icons/Wave.svg";

const getNameIcons = (data) => {
  const iconFields = ["Predator", "Bioluminescent", "Camouflage", "Electric", "Venomous"];

  const icons = iconFields.reduce((acc, key) => {
    if (data[key]) {
      acc.push(...Array(data[key]).fill(key));
    }
    return acc;
  }, []);

  return icons.map((icon, index) => <img className="text-icon" key={index} src={require(`../assets/icons/${icon}.svg`)}></img>)
}

const getCostIcons = (data) => {
  const fields = {
    "cardCost": "DrawCard",
    "eggCost": "FishEgg",
    "youngCost": "YoungFish",
    "consuming": "ConsumeFish"
  }

  const icons = Object.keys(fields).reduce((acc, key) => {
    if (data[key]) {
      acc.push(...Array(data[key]).fill(fields[key]));
    }
    return acc;
  }, []);

  return icons.map((icon, index) => <img key={index} src={require(`../assets/icons/${icon}.svg`)}></img>)
}

const getZoneIcons = (data) => {
  const fields = {
    "sunlight": "Sun",
    "twilight": "Dusk",
    "midnight": "Night"
  }

  const icons = Object.keys(fields).reduce((acc, key) => {
    if (data[key]) {
      if (key === "midnight" && data[key] === 2)
        acc.push("PlayFishBottomRow")
      else
        acc.push(fields[key]);
    }
    return acc;
  }, []);

  return icons.map((icon, index) => <img key={index} src={require(`../assets/icons/${icon}.svg`)}></img>)
}

const getZoneClass = (data) => {
  const fields = ["sunlight", "twilight", "midnight"];

  return fields.reduce((acc, key) => {
    if (data[key])
      acc += key[0]
    return acc;
  }, "");
}

const getLengthIcon = (length) => {
  let icon = "Small"
  
  if(length < 50) 
    icon = "Small";
  else if(length < 100)
    icon = "Medium";
  else
    icon = "Large";

  return <img src={require(`../assets/icons/FishLength${icon}.svg`)}></img>
}


const Card = ({ data }) => {

  return (
    <div className="card">
      <div className="name">
        <div className="title">
          {data.name}
          <div className="text-icon-container">
            {getNameIcons(data)}
          </div>
        </div>
        <div className="latin">{data.latin}</div>
      </div>
      <div className="cost">{getCostIcons(data)}</div>
      <div className={`zones ${getZoneClass(data)}`}>{getZoneIcons(data)}</div>
      <div className="points">
        {data.points}
        <img src={WaveIcon} alt="points"></img>
      </div>
      <div className="length">{data.length} cm
        {getLengthIcon(data.length)}</div>

    </div>
  )
};

export default Card;
