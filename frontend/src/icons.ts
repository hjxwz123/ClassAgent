import { defineComponent, h, type Component } from "vue";
import {
  PhActivity,
  PhArrowDown,
  PhArrowLeft,
  PhArrowRight,
  PhArrowsClockwise,
  PhBell,
  PhBookBookmark,
  PhBookOpen,
  PhCalendarCheck,
  PhCamera,
  PhCaretDown,
  PhCaretLeft,
  PhCaretRight,
  PhChartBar,
  PhChatCircle,
  PhCheck,
  PhCheckCircle,
  PhCheckSquare,
  PhClipboardText,
  PhClock,
  PhClockCounterClockwise,
  PhCloud,
  PhCopy,
  PhCornersOut,
  PhCpu,
  PhDatabase,
  PhDotsSixVertical,
  PhDotsThree,
  PhDownloadSimple,
  PhEnvelope,
  PhEye,
  PhEyeSlash,
  PhFile,
  PhFileText,
  PhFlag,
  PhFlame,
  PhFolderOpen,
  PhFloppyDisk,
  PhGearSix,
  PhGitBranch,
  PhGraduationCap,
  PhGridFour,
  PhHardDrives,
  PhHouse,
  PhIdentificationCard,
  PhInfo,
  PhKey,
  PhLightning,
  PhList,
  PhListChecks,
  PhLock,
  PhMagicWand,
  PhMagnifyingGlass,
  PhMagnifyingGlassPlus,
  PhMedal,
  PhNotePencil,
  PhPaperPlaneRight,
  PhPause,
  PhPencil,
  PhPencilLine,
  PhPlay,
  PhPlus,
  PhPlusCircle,
  PhPresentation,
  PhProhibit,
  PhPulse,
  PhQuestion,
  PhQuotes,
  PhScan,
  PhShareNetwork,
  PhShield,
  PhShieldCheck,
  PhSidebarSimple,
  PhSignIn,
  PhSignOut,
  PhSkipBack,
  PhSkipForward,
  PhSlidersHorizontal,
  PhSparkle,
  PhSpeakerHigh,
  PhSpinnerGap,
  PhStack,
  PhStar,
  PhSun,
  PhSquaresFour,
  PhTextT,
  PhTrash,
  PhTray,
  PhTrendDown,
  PhUpload,
  PhUser,
  PhUserCheck,
  PhUserMinus,
  PhUserPlus,
  PhUsers,
  PhWarning,
  PhWarningCircle,
  PhWifiHigh,
  PhX,
  PhXCircle
} from "@phosphor-icons/vue";

const DEFAULT_WEIGHT = "duotone";

function icon(component: Component) {
  return defineComponent({
    inheritAttrs: false,
    setup(_, { attrs }) {
      return () => h(component, { weight: DEFAULT_WEIGHT, ...attrs });
    }
  });
}

export const Activity = icon(PhActivity);
export const AlertCircle = icon(PhWarningCircle);
export const AlertTriangle = icon(PhWarning);
export const ArrowDown = icon(PhArrowDown);
export const ArrowLeft = icon(PhArrowLeft);
export const ArrowRight = icon(PhArrowRight);
export const Award = icon(PhMedal);
export const Ban = icon(PhProhibit);
export const BarChart2 = icon(PhChartBar);
export const Bell = icon(PhBell);
export const BookMarked = icon(PhBookBookmark);
export const BookOpen = icon(PhBookOpen);
export const CalendarCheck = icon(PhCalendarCheck);
export const Camera = icon(PhCamera);
export const Check = icon(PhCheck);
export const CheckCircle = icon(PhCheckCircle);
export const CheckSquare = icon(PhCheckSquare);
export const ChevronDown = icon(PhCaretDown);
export const ChevronLeft = icon(PhCaretLeft);
export const ChevronRight = icon(PhCaretRight);
export const ClipboardList = icon(PhClipboardText);
export const Clock = icon(PhClock);
export const Cloud = icon(PhCloud);
export const Copy = icon(PhCopy);
export const Cpu = icon(PhCpu);
export const Database = icon(PhDatabase);
export const Download = icon(PhDownloadSimple);
export const Edit2 = icon(PhPencilLine);
export const Eye = icon(PhEye);
export const EyeOff = icon(PhEyeSlash);
export const File = icon(PhFile);
export const FileCheck = icon(PhFileText);
export const FileEdit = icon(PhNotePencil);
export const FileText = icon(PhFileText);
export const Flag = icon(PhFlag);
export const Flame = icon(PhFlame);
export const FolderOpen = icon(PhFolderOpen);
export const GitBranch = icon(PhGitBranch);
export const GraduationCap = icon(PhGraduationCap);
export const Grid2X2 = icon(PhGridFour);
export const GripVertical = icon(PhDotsSixVertical);
export const HelpCircle = icon(PhQuestion);
export const History = icon(PhClockCounterClockwise);
export const Home = icon(PhHouse);
export const IdCard = icon(PhIdentificationCard);
export const Inbox = icon(PhTray);
export const Info = icon(PhInfo);
export const KeyRound = icon(PhKey);
export const Layers = icon(PhStack);
export const LayoutDashboard = icon(PhSquaresFour);
export const List = icon(PhList);
export const ListChecks = icon(PhListChecks);
export const Loader2 = icon(PhSpinnerGap);
export const Lock = icon(PhLock);
export const LogIn = icon(PhSignIn);
export const LogOut = icon(PhSignOut);
export const Mail = icon(PhEnvelope);
export const Maximize = icon(PhCornersOut);
export const MessageCircle = icon(PhChatCircle);
export const MoreHorizontal = icon(PhDotsThree);
export const PanelRight = icon(PhSidebarSimple);
export const Pause = icon(PhPause);
export const Pencil = icon(PhPencil);
export const Play = icon(PhPlay);
export const Plus = icon(PhPlus);
export const PlusCircle = icon(PhPlusCircle);
export const Presentation = icon(PhPresentation);
export const Quote = icon(PhQuotes);
export const RefreshCw = icon(PhArrowsClockwise);
export const Save = icon(PhFloppyDisk);
export const Scan = icon(PhScan);
export const Search = icon(PhMagnifyingGlass);
export const Send = icon(PhPaperPlaneRight);
export const Server = icon(PhHardDrives);
export const Settings = icon(PhGearSix);
export const Share2 = icon(PhShareNetwork);
export const Shield = icon(PhShield);
export const ShieldCheck = icon(PhShieldCheck);
export const SkipBack = icon(PhSkipBack);
export const SkipForward = icon(PhSkipForward);
export const SlidersHorizontal = icon(PhSlidersHorizontal);
export const Sparkles = icon(PhSparkle);
export const Star = icon(PhStar);
export const Sun = icon(PhSun);
export const Trash2 = icon(PhTrash);
export const TrendingDown = icon(PhTrendDown);
export const Type = icon(PhTextT);
export const Upload = icon(PhUpload);
export const User = icon(PhUser);
export const UserCheck = icon(PhUserCheck);
export const UserPlus = icon(PhUserPlus);
export const UserX = icon(PhUserMinus);
export const Users = icon(PhUsers);
export const Volume2 = icon(PhSpeakerHigh);
export const Wand2 = icon(PhMagicWand);
export const WandSparkles = icon(PhMagicWand);
export const Wifi = icon(PhWifiHigh);
export const X = icon(PhX);
export const XCircle = icon(PhXCircle);
export const Zap = icon(PhLightning);
export const ZoomIn = icon(PhMagnifyingGlassPlus);
