import { useColorScheme } from "@mui/joy/styles";
import IconButton from "@mui/joy/IconButton";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";

export default function ThemeToggle() {
  const { mode, systemMode, setMode } = useColorScheme();
  const isDark = mode === "dark" || (mode === "system" && systemMode === "dark");
  return (
    <IconButton
      variant="soft"
      color="neutral"
      onClick={() => setMode(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {isDark ? <LightModeIcon /> : <DarkModeIcon />}
    </IconButton>
  );
}
