import Image from "next/image";
import Link from "next/link";

import logo from "../../../../docs/ui/cyverse_logo.png";

interface BrandMarkProps {
  compact?: boolean;
  inverse?: boolean;
  href?: string;
  onClick?: () => void;
}

export function BrandMark({
  compact = false,
  inverse = false,
  href = "/dashboard",
  onClick,
}: BrandMarkProps) {
  const content = (
    <>
      <span className="brand-mark__image">
        <Image src={logo} alt="CyVerse Logo" priority={!compact} sizes={compact ? "38px" : "76px"} />
      </span>
      <span className="brand-mark__copy">
        <strong className={inverse ? "text-white" : ""}>CyVerse</strong>
        {!compact && <small>Detect · Deceive · Defend</small>}
      </span>
    </>
  );

  const className = `brand-mark ${compact ? "brand-mark--compact" : ""}`;

  if (href) {
    return (
      <Link href={href} onClick={onClick} className={className} aria-label="CyVerse Home">
        {content}
      </Link>
    );
  }

  return (
    <div className={className} onClick={onClick}>
      {content}
    </div>
  );
}
