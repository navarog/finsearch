import React, { useReducer, useState, useMemo } from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import "./App.scss";
import cards from "./assets/cards.json";
import Card from "./card/Card";
import Search, { handleSearch } from "./search/Search";

const DISPLAYED_CARDS_INCREMENT = 30;

function App() {
  const [cardState, triggerSearch] = useReducer(handleSearch, {
    allCards: cards.reduce(
      (acc, card) => ({ ...acc, [card.id]: card }),
      {}),
    filteredCardIds: cards.map((card) => card.id),
  });

  const [displayedCardsCount, setDisplayedCardsCount] = useState(
    DISPLAYED_CARDS_INCREMENT
  );

  const displayedCardIds = useMemo(
    () => cardState.filteredCardIds.slice(0, displayedCardsCount),
    [cardState.filteredCardIds, displayedCardsCount]
  );

  function displayMoreCards() {
    setDisplayedCardsCount(displayedCardsCount + DISPLAYED_CARDS_INCREMENT);
  }

  return (
    <div className="App">
      <Search cardState={cardState} triggerSearch={triggerSearch} />
      <InfiniteScroll
        dataLength={displayedCardIds.length}
        next={displayMoreCards}
        hasMore={displayedCardIds.length < cardState.filteredCardIds.length}
      >
        <div className="cards-container">
          {displayedCardIds.map((id) => (
            <Card key={id} data={cardState.allCards[id]} />
          ))}
        </div>
      </InfiniteScroll>
    </div>
  );
}

export default App;
