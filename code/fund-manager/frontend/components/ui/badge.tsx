import { mergeProps } from "@base-ui/react/merge-props";
import { useRender } from "@base-ui/react/use-render";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "group/badge inline-flex h-6 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border px-2.5 py-0.5 text-[11px] font-medium whitespace-nowrap transition-all focus-visible:ring-2 focus-visible:ring-ring [&>svg]:pointer-events-none [&>svg]:size-3!",
  {
    variants: {
      variant: {
        default: "border-primary/20 bg-primary/10 text-primary dark:border-primary/30 dark:bg-primary/16 dark:text-primary-foreground",
        secondary: "border-border/80 bg-secondary/70 text-secondary-foreground",
        destructive: "border-danger/20 bg-danger/10 text-danger dark:border-danger/28 dark:bg-danger/16",
        outline: "border-border/80 bg-transparent text-muted-foreground",
        ghost: "border-transparent bg-secondary/45 text-muted-foreground",
        link: "border-transparent bg-transparent px-0 text-primary",
        success: "border-success/20 bg-success/10 text-success dark:border-success/28 dark:bg-success/16",
        warning: "border-warning/20 bg-warning/12 text-warning dark:border-warning/28 dark:bg-warning/18",
      },
    },
    defaultVariants: {
      variant: "outline",
    },
  }
);

function Badge({
  className,
  variant = "outline",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  });
}

export { Badge, badgeVariants };
