import { NewsFeed } from "@/components/NewsFeed";
import { vertical } from "@/config/verticals";
import { Helmet } from "react-helmet-async";

const Index = () => {
  return (
    <>
      <Helmet>
        <title>{vertical.metaTitle}</title>
        <meta name="description" content={vertical.metaDescription} />
      </Helmet>
      <NewsFeed />
    </>
  );
};

export default Index;
