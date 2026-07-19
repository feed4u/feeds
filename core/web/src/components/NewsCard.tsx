import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ExternalLink, Clock } from "lucide-react";
import { NewsItem, getCategoryLabel, formatFeedTypeLabel } from "@/data/newsData";
import { formatDistanceToNow } from "date-fns";

interface NewsCardProps {
  item: NewsItem;
  index: number;
  onCategoryClick?: (category: string) => void;
  onSmartGroupClick?: (group: string) => void;
  selectedSmartGroup?: string;
  selectedCategory?: string;
}

export function NewsCard({ item, index, onCategoryClick, onSmartGroupClick, selectedSmartGroup, selectedCategory }: NewsCardProps) {
  const getCategoryVariant = (category: string) => {
    switch (category) {
      case 'vulnerabilities':
      case 'malware':
      case 'leaks':
        return 'destructive';
      case 'threat-intel':
      case 'cybercrime':
      case 'crypto':
        return 'accent';
      case 'dfir':
        return 'success';
      default:
        return 'category';
    }
  };

  return (
    <Card
      className="group p-5 gradient-card border-border hover:border-primary/30 transition-all duration-300 animate-fade-in"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="source" className="text-[13px]">{item.source}</Badge>
          <Badge variant="outline" className="text-[11px] uppercase tracking-wide">
            {formatFeedTypeLabel(item.feedType)}
          </Badge>
          <Badge
            variant={getCategoryVariant(item.category)}
            className={`text-[13px] cursor-pointer hover:opacity-80 transition-opacity ${
              selectedCategory === item.category ? 'ring-2 ring-primary ring-offset-2' : ''
            }`}
            onClick={(e) => {
              e.preventDefault();
              onCategoryClick?.(item.category);
            }}
          >
            {getCategoryLabel(item.category)}
          </Badge>
        </div>
        <div className="flex items-center gap-1.5 text-[13px] text-muted-foreground font-mono shrink-0">
          <Clock className="h-3 w-3" />
          {formatDistanceToNow(item.date, { addSuffix: true })}
        </div>
      </div>

      <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-primary transition-colors">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-start gap-2"
        >
          {item.title}
          <ExternalLink className="h-4 w-4 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity mt-0.5" />
        </a>
      </h3>

      <p className="text-[15px] text-muted-foreground leading-relaxed line-clamp-3">
        {item.summary}
      </p>

      {item.smartGroups.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border">
          {item.smartGroups.map((group) => {
            const isSelected = selectedSmartGroup === group;
            return (
              <button
                key={group}
                onClick={(e) => {
                  e.preventDefault();
                  onSmartGroupClick?.(group);
                }}
                className={`text-[13px] font-mono px-2.5 py-1 rounded transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-primary text-primary-foreground font-semibold'
                    : 'text-muted-foreground bg-muted/50 hover:bg-muted hover:text-foreground'
                }`}
              >
                #{group}
              </button>
            );
          })}
        </div>
      )}
    </Card>
  );
}
