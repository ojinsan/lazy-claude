import * as React from "react";

import { cn } from "@/lib/utils";

function Card({
  className,
  size = "default",
  ...props
}: React.ComponentProps<"div"> & { size?: "default" | "sm" }) {
  return (
    <div
      data-slot="card"
      data-size={size}
      className={cn(
        "group/card flex flex-col gap-4 overflow-hidden rounded-2xl border border-border/80 bg-card text-sm text-card-foreground shadow-[0_1px_1px_rgba(15,23,42,0.04),0_18px_48px_rgba(15,23,42,0.08)] dark:shadow-[0_0_0_1px_rgba(255,255,255,0.02),0_22px_45px_rgba(0,0,0,0.24)] data-[size=sm]:gap-3",
        className
      )}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "grid auto-rows-min items-start gap-1.5 px-5 pt-5 data-[size=sm]:px-4 data-[size=sm]:pt-4 has-data-[slot=card-action]:grid-cols-[1fr_auto]",
        className
      )}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn("font-heading text-base font-semibold tracking-[-0.02em] text-foreground", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card-description" className={cn("text-sm text-muted-foreground", className)} {...props} />;
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div data-slot="card-action" className={cn("col-start-2 row-span-2 row-start-1 self-start justify-self-end", className)} {...props} />
  );
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card-content" className={cn("px-5 pb-5 data-[size=sm]:px-4 data-[size=sm]:pb-4", className)} {...props} />;
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center border-t border-border/70 bg-secondary/35 px-5 py-4 data-[size=sm]:px-4 data-[size=sm]:py-3", className)}
      {...props}
    />
  );
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
};
