import { NewsFeed } from "@/components/NewsFeed";
import { vertical } from "@/config/verticals";
import { Helmet } from "react-helmet-async";

const Index = () => {
  return (
    <>
      <Helmet>
        <title>{vertical.metaTitle}</title>
        <meta name="description" content="Real-time security news feed aggregating threat intelligence, vulnerabilities, and cybersecurity updates from trusted sources worldwide." />
      </Helmet>
      <NewsFeed />
    </>
  );
};

export default Index;
