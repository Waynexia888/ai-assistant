import { searchResults } from "../../data/dashboardData";
import { Icon } from "../common/Icon";
import { SearchResultCard } from "../tools/SearchResultCard";

export function DocumentSearchPanel() {
  return (
    <section className="search-panel">
      <div className="panel-head center"><h3>Document Search</h3></div>
      <div className="search-controls">
        <div className="search-input"><Icon name="search" /><span>Search documents...</span></div>
        <button className="kb-select">All Knowledge Bases<span>⌄</span></button>
        <a>Advanced</a>
      </div>
      <div className="results">
        {searchResults.map((result) => <SearchResultCard result={result} key={result[0]} />)}
      </div>
      <a className="panel-link">View all results (128) <span>→</span></a>
    </section>
  );
}
