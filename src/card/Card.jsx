import React, { useRef, useEffect, useState } from "react";
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

  return icons.map((icon, index) => <img className="text-icon" key={index} src={require(`../assets/icons/${icon}.svg`)} alt={icon}></img>)
}

const getCostIcons = (data) => {
  const fields = {
    "cardCost": "DrawCard",
    "eggCost": "FishEgg",
    "youngCost": "YoungFish",
    "consuming": "ConsumeFish",
    "schoolFishCost": "SchoolFish"
  }

  const icons = Object.keys(fields).reduce((acc, key) => {
    if (data[key]) {
      acc.push(...Array(data[key]).fill(fields[key]));
    }
    return acc;
  }, []);

  if (icons.length === 0)
    icons.push('NoCost');

  return icons.map((icon, index) => <img key={index} src={require(`../assets/icons/${icon}.svg`)} alt={icon}></img>)
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

  if (data.coralCost) {
    const [coralType, countStr] = data.coralCost.split(':');
    const count = parseInt(countStr);
    const iconName = coralType.charAt(0).toUpperCase() + coralType.slice(1) + 'Coral';
    const coralImgs = Array(count).fill(null).map((_, i) =>
      <img className={iconName} key={`c${i}`} src={require(`../assets/icons/${iconName}.svg`)} alt={iconName}/>
    );
    return icons.map((icon, index) =>
      <div key={index} style={{display:'flex',flexDirection:'row',alignItems:'center',gap:'1cqw'}}>
        <img src={require(`../assets/icons/${icon}.svg`)} alt={icon}/>
        {coralImgs}
      </div>
    );
  }

  return icons.map((icon, index) => <img key={index} src={require(`../assets/icons/${icon}.svg`)} alt={icon}></img>)
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

  if (length < 50)
    icon = "Small";
  else if (length < 150)
    icon = "Medium";
  else
    icon = "Large";

  return <img src={require(`../assets/icons/FishLength${icon}.svg`)} alt={icon}></img>
}

const getCardBackground = (data) => {
  const background = data.band || "base";
  return require(`../assets/backgrounds/${background}.webp`);
}

const processAbilityText = (text, matchRows = true) => {
  // Define the regex components
  const rowRegex = "\\[(?:[^\\[\\]]+)](?:\\s*\\+\\s*\\[[^\\[\\]]+])+";
  const iconRegex = "\\d+ ?\\[Wave\\]|[a-zA-Z0-9 ()\\+,:']+|\\[[\\w-]+\\]";
  const fullRegex = matchRows
    ? new RegExp(`(${rowRegex}|${iconRegex})`, "gi")
    : new RegExp(`(${iconRegex})`, "gi");

  const parts = text.split(fullRegex).filter(p => p && p.trim());
  const mapped = parts.map((part, index) => {
    if (part.match(rowRegex))
      return <div key={index} className="ability-row">{processAbilityText(part, false)}</div>;
    if (part.includes("[Wave]"))
      return <div key={index} className="ability-points">{part.split("[Wave]")[0].trim()}<img src={WaveIcon} alt="Wave"></img></div>;
    if (part.startsWith("[") && part.endsWith("]")) {
      const name = part.slice(1, -1);
      return <img className={name} key={index} src={require(`../assets/icons/${name}.svg`)} alt={name}></img>;
    }
    return <div key={index} className="ability-text">{part.trim()}</div>;
  });

  const result = [];
  let iconRun = [];

  const flushIconRun = () => {
    if (iconRun.length > 1) {
      const counts = {};
      iconRun.forEach(el => { counts[el.props.className] = (counts[el.props.className] || 0) + 1; });
      const countClasses = Object.entries(counts).map(([name, n]) => `${name}-${n}`).join(' ');
      result.push(
        <span key={`ig-${result.length}`} className={`icon-group ${countClasses}`}>
          {iconRun}
        </span>
      );
    } else {
      iconRun.forEach(el => result.push(el));
    }
    iconRun = [];
  };

  mapped.forEach(el => {
    if (el.type === 'img') iconRun.push(el);
    else { flushIconRun(); result.push(el); }
  });
  flushIconRun();

  return result;
}

const getAbility = (data) => {
  const abilitiesWithBackground = ["IfActivated", "GameEnd"]
  const style = {}
  const abilityTexts = {
    "IfActivated": "IF ACTIVATED:",
    "GameEnd": "GAME END:",
    "WhenPlayed": "WHEN PLAYED:"
  }

  if (abilitiesWithBackground.includes(data.abilityType))
    style.backgroundImage = `url(${require(`../assets/backgrounds/${data.abilityType}.png`)})`

  if (data.abilityType === 'IfActivated' && data.ability?.includes('also, if')) {
    const alsoIfIdx = data.ability.indexOf('also, if');
    const costPart = data.ability.substring(0, alsoIfIdx).trim();
    const effectPart = data.ability.substring(alsoIfIdx);
    return <>
      <div className={`ability ${effectPart && "squished"}`} style={style}>
        <div className="ability-text bold">{abilityTexts[data.abilityType]}</div>
        {costPart && processAbilityText(costPart)}
      </div>
      <div className="ability also-if" style={style}>
        {processAbilityText(effectPart)}
      </div>
    </>
  }

  return <div className="ability" style={style}><div className="ability-text bold">{abilityTexts[data.abilityType]}</div> {data.ability && processAbilityText(data.ability)}</div>
}

const addGroupMarker = (data) => {
  if (data.group === "starter")
    return <>
      <div className="corner-overlay top-left"></div>
      <div className="corner-overlay bottom-right"></div>
    </>

  else
    return <></>

}


const measureFirstLineWidth = (element) => {
  if (!element) return 0;

  // Create a range to measure the text
  const range = document.createRange();
  const text = element.childNodes[0]; // Get the text node
  
  if (!text) return 0;

  // Find the index where the line breaks
  let low = 0;
  let high = text.length;
  let mid;
  
  while (low < high) {
    mid = Math.floor((low + high + 1) / 2);
    range.setStart(text, 0);
    range.setEnd(text, mid);
    const rects = range.getClientRects();
    
    // If we have more than one rect, we've gone too far
    if (rects.length > 1) {
      high = mid - 1;
    } else {
      low = mid;
    }
  }

  // Measure the final width
  range.setStart(text, 0);
  range.setEnd(text, low);
  const rects = range.getClientRects();
  
  return rects.length > 0 ? rects[0].width : 0;
};

const Card = ({ data }) => {
  const containerRef = useRef(null);
  const [firstLineWidth, setFirstLineWidth] = useState(0);

  useEffect(() => {
    const updateWidth = () => {
      const width = measureFirstLineWidth(containerRef.current);
      setFirstLineWidth(width);
    };

    // Initial measurement
    updateWidth();

    // Add resize observer to handle window/container size changes
    const resizeObserver = new ResizeObserver(updateWidth);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  return (
    <div className="card" style={{ backgroundImage: `url(${getCardBackground(data)})` }}>
      <div className="name">
        <div className="title" ref={containerRef}>
          {data.name}
          <div className="text-icon-container" style={{left: `calc(50cqw + 0.5 * ${firstLineWidth}px)`}}>
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
        {getLengthIcon(data.length)}
      </div>
      <div className="ability-container">
        {getAbility(data)}
      </div>
      <img className="silhouette" src={require(`../assets/silhouettes/${data.id}.webp`)} alt="Fish silhouette"></img>
      {data.expansion === 'sr' && <img className="expansion-logo" src={require('../assets/icons/SRLogo.svg').default} alt="S&R"></img>}
      <div className="description">
        {data.description}
      </div>
      {addGroupMarker(data)}
    </div>
  );
};
export default Card;
