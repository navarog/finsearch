import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  TextField,
  ThemeProvider,
  Tooltip,
  createTheme,
} from "@mui/material";
import FlexSearch from "flexsearch";
import { useEffect, useState, useMemo } from "react";
import "./Search.css";
import FishFromHand from "../assets/icons/FishFromHand.svg";

const cardIndex = FlexSearch.Document({
  tokenize: "full",
  document: {
    id: "id",
    index: ["name", "latin", "description"],
  },
});

import("../assets/cards.json").then((cards) => {
  cards.default
    .sort((a, b) => a.id - b.id)
    .forEach((card) => cardIndex.add(card));
});

const fields = [
  "group",
  "length",
];

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
    return query.group[card.group]; // TODO: filter for the future
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
              <TextField
                variant="standard"
                label="Search the cards"
                className="search-input"
                value={query.text}
                onChange={(e) => setQuery({ ...query, text: e.target.value })}
                onClick={(e) => e.stopPropagation()}
                placeholder="Search the cards by its name"
              />
              <div className="search-count-container">
                  <div
                    className="search-count"
                  >
                    {stats.group.main || 0}
                    <img src={FishFromHand} alt="Cards" />
                  </div>
              </div>
            </div>
          </AccordionSummary>
          <AccordionDetails>
            {/* <div className="search-details">
              <Tooltip title="Filter out cards by personality">
                <div className="row">
                  <img
                    src={Shy}
                    alt="Shy"
                    className={`personality ${
                      query.personality.Shy ? "" : "disabled"
                    }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        personality: {
                          ...query.personality,
                          Shy: !query.personality.Shy,
                        },
                      })
                    }
                  />
                  <img
                    src={Playful}
                    alt="Playful"
                    className={`personality ${
                      query.personality.Playful ? "" : "disabled"
                    }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        personality: {
                          ...query.personality,
                          Playful: !query.personality.Playful,
                        },
                      })
                    }
                  />
                  <img
                    src={Helpful}
                    alt="Helpful"
                    className={`personality ${
                      query.personality.Helpful ? "" : "disabled"
                    }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        personality: {
                          ...query.personality,
                          Helpful: !query.personality.Helpful,
                        },
                      })
                    }
                  />
                  <img
                    src={Aggressive}
                    alt="Aggressive"
                    className={`personality ${
                      query.personality.Aggressive ? "" : "disabled"
                    }`}
                    onClick={(e) =>
                      setQuery({
                        ...query,
                        personality: {
                          ...query.personality,
                          Aggressive: !query.personality.Aggressive,
                        },
                      })
                    }
                  />
                </div>
              </Tooltip>
            </div> */}
          </AccordionDetails>
        </Accordion>
      </div>
    </ThemeProvider>
  );
}

export default Search;
