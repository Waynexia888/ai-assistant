export function SearchResultCard({ result }) {
  const [title, meta, tag] = result;

  return (
    <article>
      <div>
        <h4>{title}</h4>
        <p>{meta}</p>
      </div>
      <span className={tag.toLowerCase()}>{tag}</span>
    </article>
  );
}
