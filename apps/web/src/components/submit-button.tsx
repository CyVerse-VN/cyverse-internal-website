"use client";

import { Loader2 } from "lucide-react";
import { useFormStatus } from "react-dom";

import { Button, type ButtonProps } from "@/components/ui/button";

interface SubmitButtonProps extends ButtonProps {
  children: React.ReactNode;
  pendingLabel?: string;
}

export function SubmitButton({
  children,
  className,
  pendingLabel = "Saving…",
  ...props
}: SubmitButtonProps) {
  const { pending } = useFormStatus();

  return (
    <Button
      className={className}
      type="submit"
      disabled={pending}
      aria-busy={pending}
      {...props}
    >
      {pending ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>{pendingLabel}</span>
        </>
      ) : (
        children
      )}
    </Button>
  );
}

