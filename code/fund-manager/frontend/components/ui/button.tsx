import { Button as ButtonPrimitive } from "@base-ui/react/button";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border text-sm font-medium whitespace-nowrap transition-all outline-none select-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 active:not-aria-[haspopup]:translate-y-px [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "border-primary/30 bg-primary text-primary-foreground shadow-[0_10px_24px_rgba(94,106,210,0.18)] hover:bg-primary/92 dark:shadow-[0_12px_30px_rgba(113,112,255,0.28)]",
        outline:
          "border-border/80 bg-secondary/50 text-secondary-foreground hover:bg-secondary hover:text-foreground",
        secondary:
          "border-border/70 bg-card text-foreground hover:bg-accent hover:text-accent-foreground",
        ghost:
          "border-transparent bg-transparent text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
        destructive:
          "border-danger/30 bg-danger/15 text-danger hover:bg-danger/22",
        link: "border-transparent bg-transparent px-0 text-primary hover:text-primary/80",
      },
      size: {
        default: "h-9 px-4",
        xs: "h-7 rounded-lg px-2.5 text-xs",
        sm: "h-8 rounded-lg px-3 text-[13px]",
        lg: "h-10 px-5 text-[15px]",
        icon: "size-9",
        "icon-xs": "size-7 rounded-lg",
        "icon-sm": "size-8 rounded-lg",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
