import { LucideIcon } from "lucide-react";
import * as Icons from "lucide-react";
import { cn } from "@/lib/utils";

interface ServiceTileProps {
  name: string;
  url: string;
  icon: string;
  color: string;
  isCompact?: boolean;
}

const ServiceTile = ({ name, url, icon, color, isCompact = false }: ServiceTileProps) => {
  // Get the icon component from lucide-react
  const iconName = icon.split('-').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join('') as keyof typeof Icons;
  
  const IconComponent = (Icons[iconName] || Icons.Server) as LucideIcon;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "group relative overflow-hidden rounded-xl transition-all duration-300",
        "bg-gradient-to-br from-card to-card/80",
        "border border-border/50 hover:border-border",
        "hover:scale-[1.02] hover:shadow-2xl hover:bg-card-hover",
        isCompact ? "p-4" : "p-6"
      )}
      style={{
        boxShadow: `0 4px 20px ${color}15`,
      }}
    >
      {/* Accent bar */}
      <div 
        className="absolute top-0 left-0 right-0 h-1 rounded-t-xl transition-all duration-300 group-hover:h-1.5"
        style={{ backgroundColor: color }}
      />

      <div className={cn(
        "flex items-center gap-4",
        isCompact ? "flex-row" : "flex-col text-center"
      )}>
        {/* Icon */}
        <div 
          className={cn(
            "rounded-xl flex items-center justify-center transition-all duration-300",
            "group-hover:scale-110",
            isCompact ? "w-12 h-12" : "w-16 h-16"
          )}
          style={{ backgroundColor: `${color}20` }}
        >
          <IconComponent 
            className={cn(
              "transition-all duration-300",
              isCompact ? "w-6 h-6" : "w-8 h-8"
            )}
            style={{ color }}
          />
        </div>

        {/* Name */}
        <div className={cn(
          "flex-1",
          isCompact ? "text-left" : "text-center"
        )}>
          <h3 className={cn(
            "font-semibold text-foreground transition-colors duration-300",
            "group-hover:text-primary",
            isCompact ? "text-base" : "text-lg"
          )}>
            {name}
          </h3>
          {!isCompact && (
            <p className="text-sm text-muted-foreground mt-1">
              {new URL(url).hostname}
            </p>
          )}
        </div>

        {/* External link icon */}
        <Icons.ExternalLink 
          className={cn(
            "opacity-0 group-hover:opacity-100 transition-opacity duration-300",
            isCompact ? "w-4 h-4" : "w-5 h-5",
            "text-muted-foreground"
          )}
        />
      </div>
    </a>
  );
};

export default ServiceTile;
