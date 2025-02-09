import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  ThemeProvider,
  Tooltip,
  createTheme,
} from "@mui/material";
import FlexSearch from "flexsearch";
import { useEffect, useState, useMemo } from "react";
import EmojiTextField, { ALLOWED_EMOJIS } from "./EmojiTextField";
import EmojiButton from "./EmojiButton";
import "./Search.scss";

import FishFromHand from "../assets/icons/FishFromHand.svg";
import StarterIcon from "../assets/icons/StarterIcon.svg";
import LengthSmall from "../assets/icons/FishLengthSmall.svg";
import LengthMedium from "../assets/icons/FishLengthMedium.svg";
import LengthLarge from "../assets/icons/FishLengthLarge.svg";
import Sunlight from "../assets/icons/Sun.svg";
import Twilight from "../assets/icons/Dusk.svg";
import Midnight from "../assets/icons/Night.svg";
import Bioluminescent from "../assets/icons/Bioluminescent.svg";
import Camouflage from "../assets/icons/Camouflage.svg";
import Electric from "../assets/icons/Electric.svg";
import Predator from "../assets/icons/Predator.svg";
import Venomous from "../assets/icons/Venomous.svg";

const cardIndex = FlexSearch.Document({
  tokenize: "full",
  document: {
    id: "id",
    index: ["name", "latin", "ability"],
  },
});

import("../assets/cards.json").then((cards) => {
  cards.default
    .sort((a, b) => a.id - b.id)
    .forEach((card) => cardIndex.add(card));
});

const fields = [
  "group",
];

const filterLength = (query, length) => {
  let size = "small";

  if (length < 50)
    size = "small";
  else if (length < 150)
    size = "medium";
  else
    size = "large";

  return query[size];
}

const filterZones = (query, card) => {
  return Object.keys(query).reduce((acc, key) =>
    acc && (query[key] || (!query[key] && !card[key])), true
  )
}

const filterTags = (query, card) => {
  return Object.keys(query).reduce((acc, key) =>
    acc && (!query[key] || card[key]), true
  )
}

export function handleSearch(state, query) {
  const searchedIds = query.text
    ? [
      ...new Set(
        cardIndex
          .search(query.text)
          .reduce((acc, item) => [...acc, ...item.result], [])
      ),
    ]
    : Object.values(state.allCards).map((card) => card.id);
  const filteredIds = searchedIds.filter((id) => {
    const card = state.allCards[id];
    return query.group[card.group] && filterLength(query.length, card.length) && filterZones(query.zones, card) && filterTags(query.tags, card);
  });

  return { ...state, filteredCardIds: filteredIds.sort((a, b) => a - b) };
}

function Search({ cardState, triggerSearch }) {
  const defaultQuery = {
    text: "",
    group: {
      main: true,
      starter: true,
    },
    length: {
      small: true,
      medium: true,
      large: true,
    },
    zones: {
      sunlight: true,
      twilight: true,
      midnight: true
    },
    tags: {
      Bioluminescent: false,
      Camouflage: false,
      Electric: false,
      Predator: false,
      Venomous: false
    }
  };
  const [query, setQuery] = useState(defaultQuery);

  useEffect(() => {
    triggerSearch(query);
  }, [query, triggerSearch]);

  const stats = useMemo(() => {
    return cardState.filteredCardIds
      .map((id) => cardState.allCards[id])
      .reduce(
        (acc, card) => {
          fields.forEach((field) => {
            if (!acc[field][card[field]]) acc[field][card[field]] = 0;
            acc[field][card[field]]++;
          });
          return acc;
        },
        fields.reduce((obj, field) => ({ ...obj, [field]: {} }), {})
      );
  }, [cardState]);

  const theme = createTheme({
    typography: {
      fontFamily: "Panforte Pro, sans-serif",
      fontSize: 15,
    },
  });

  return (
    <ThemeProvider theme={theme}>
      <div className="search-container">
        <Accordion>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="panel1-content"
            id="panel1-header"
          >
            <div className="search-summary">
                <EmojiTextField
                  query={query}
                  setQuery={setQuery}
                  label="Search the cards"
                  placeholder="Search the cards by their names"
                  onClick={(e) => e.stopPropagation()}
                />
              <div className="search-count-container">
                <Tooltip title="Main cards">
                  <div
                    className={`search-count ${query.group.main ? "" : "disabled"
                      }`}
                    onClick={(e) => {
                      setQuery({
                        ...query,
                        group: { ...query.group, main: !query.group.main },
                      });
                      e.stopPropagation();
                    }}
                  >
                    {stats.group.main || 0}
                    <img src={FishFromHand} alt="Cards" />
                  </div>
                </Tooltip>
                <Tooltip title="Starter cards">
                  <div
                    className={`search-count ${query.group.starter ? "" : "disabled"
                      }`}
                    onClick={(e) => {
                      setQuery({
                        ...query,
                        group: { ...query.group, starter: !query.group.starter },
                      });
                      e.stopPropagation();
                    }}
                  >
                    {stats.group.starter || 0}
                    <img src={StarterIcon} alt="Starters" />
                  </div>
                </Tooltip>
              </div>
            </div>
          </AccordionSummary>
          <AccordionDetails>
            Filter by the abilities
            <Tooltip title="Search by the icons in the ability powers">
              <div className="emoji-row">
                {ALLOWED_EMOJIS.map((emoji, index) => (
                  <EmojiButton key={index} query={query} setQuery={setQuery} icon={emoji} />
                ))}
              </div>
            </Tooltip>
            Filter by the fish characteristics
            <div className="search-details">
              {/* TODO: show counts for each filter by using stats */}
              <Tooltip title="Filter out cards by zones">
                <div className="row zones-row">
                  <img
                    src={Sunlight}
                    alt="Sunlight"
                    className={`zone ${query.zones.sunlight ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        zones: {
                          ...query.zones,
                          sunlight: !query.zones.sunlight,
                        },
                      })
                    }
                  />
                  <img
                    src={Twilight}
                    alt="Twilight"
                    className={`zone ${query.zones.twilight ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        zones: {
                          ...query.zones,
                          twilight: !query.zones.twilight,
                        },
                      })
                    }
                  />
                  <img
                    src={Midnight}
                    alt="Midnight"
                    className={`zone ${query.zones.midnight ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        zones: {
                          ...query.zones,
                          midnight: !query.zones.midnight,
                        },
                      })
                    }
                  />
                </div>
              </Tooltip>
              <Tooltip title="Filter out cards by tags">
                <div className="row tags-row">
                  <img
                    src={Bioluminescent}
                    alt="Bioluminescent"
                    className={`tag ${query.tags.Bioluminescent ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        tags: {
                          ...query.tags,
                          Bioluminescent: !query.tags.Bioluminescent,
                        },
                      })
                    }
                  />
                  <img
                    src={Camouflage}
                    alt="Camouflage"
                    className={`tag ${query.tags.Camouflage ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        tags: {
                          ...query.tags,
                          Camouflage: !query.tags.Camouflage,
                        },
                      })
                    }
                  />
                  <img
                    src={Electric}
                    alt="Electric"
                    className={`tag ${query.tags.Electric ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        tags: { ...query.tags, Electric: !query.tags.Electric },
                      })
                    }
                  />
                  <img
                    src={Predator}
                    alt="Predator"
                    className={`tag ${query.tags.Predator ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        tags: { ...query.tags, Predator: !query.tags.Predator },
                      })
                    }
                  />
                  <img
                    src={Venomous}
                    alt="Venomous"
                    className={`tag ${query.tags.Venomous ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        tags: { ...query.tags, Venomous: !query.tags.Venomous },
                      })
                    }
                  />
                </div>
              </Tooltip>
              <Tooltip title="Filter out cards by length">
                <div className="row length-row">
                  <img
                    src={LengthSmall}
                    alt="Small"
                    className={`fish-length ${query.length.small ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        length: {
                          ...query.length,
                          small: !query.length.small,
                        },
                      })
                    }
                  />
                  <img
                    src={LengthMedium}
                    alt="Medium"
                    className={`fish-length ${query.length.medium ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        length: {
                          ...query.length,
                          medium: !query.length.medium,
                        },
                      })
                    }
                  />
                  <img
                    src={LengthLarge}
                    alt="Large"
                    className={`fish-length ${query.length.large ? "" : "disabled"
                      }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        length: {
                          ...query.length,
                          large: !query.length.large,
                        },
                      })
                    }
                  />
                </div>
              </Tooltip>
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
    </ThemeProvider>
  );
}

export default Search;
