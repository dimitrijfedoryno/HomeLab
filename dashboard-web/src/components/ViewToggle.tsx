import { LayoutGrid, List } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ViewMode = "grid" | "compact";

interface ViewToggleProps {
  viewMode: ViewMode;
  onToggle: (mode: ViewMode) => void;
}

const ViewToggle = ({ viewMode, onToggle }: ViewToggleProps) => {
  return (
    <div className="flex items-center gap-2 bg-card rounded-lg p-1 border border-border/50">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onToggle("grid")}
        className={cn(
          "gap-2 transition-all duration-200",
          viewMode === "grid" 
            ? "bg-accent text-accent-foreground" 
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <LayoutGrid className="w-4 h-4" />
        <span className="hidden sm:inline">Grid</span>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onToggle("compact")}
        className={cn(
          "gap-2 transition-all duration-200",
          viewMode === "compact" 
            ? "bg-accent text-accent-foreground" 
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <List className="w-4 h-4" />
        <span className="hidden sm:inline">Compact</span>
      </Button>
    </div>
  );
};

export default ViewToggle;
