import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

const SearchBar = ({ value, onChange }: SearchBarProps) => {
  return (
    <div className="relative max-w-md w-full">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
      <Input
        type="text"
        placeholder="Vyhledat službu..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-10 bg-card border-border/50 focus:border-border h-12 text-base"
      />
    </div>
  );
};

export default SearchBar;
