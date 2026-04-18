"use client";

import { Tabs as TabsPrimitive } from "@base-ui/react/tabs";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

function Tabs({
  className,
  orientation = "horizontal",
  ...props
}: TabsPrimitive.Root.Props) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      data-orientation={orientation}
      className={cn("group/tabs flex gap-4 data-horizontal:flex-col", className)}
      {...props}
    />
  );
}

const tabsListVariants = cva(
  "inline-flex w-fit items-center gap-1 rounded-full border border-border/80 bg-secondary/55 p-1 text-muted-foreground",
  {
    variants: {
      variant: {
        default: "",
        line: "rounded-none border-0 bg-transparent p-0",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

function TabsList({
  className,
  variant = "default",
  ...props
}: TabsPrimitive.List.Props & VariantProps<typeof tabsListVariants>) {
  return <TabsPrimitive.List data-slot="tabs-list" data-variant={variant} className={cn(tabsListVariants({ variant }), className)} {...props} />;
}

function TabsTrigger({ className, ...props }: TabsPrimitive.Tab.Props) {
  return (
    <TabsPrimitive.Tab
      data-slot="tabs-trigger"
      className={cn(
        "relative inline-flex min-h-9 flex-1 items-center justify-center rounded-full border border-transparent px-3 py-1.5 text-sm font-medium whitespace-nowrap text-muted-foreground transition-all hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 data-active:border-border/80 data-active:bg-card data-active:text-foreground data-active:shadow-[0_0_0_1px_rgba(255,255,255,0.02),0_12px_24px_rgba(0,0,0,0.18)] group-data-[variant=line]/tabs-list:rounded-none group-data-[variant=line]/tabs-list:border-b-2 group-data-[variant=line]/tabs-list:px-0 group-data-[variant=line]/tabs-list:py-2 group-data-[variant=line]/tabs-list:data-active:border-primary group-data-[variant=line]/tabs-list:data-active:bg-transparent group-data-[variant=line]/tabs-list:data-active:shadow-none",
        className
      )}
      {...props}
    />
  );
}

function TabsContent({ className, ...props }: TabsPrimitive.Panel.Props) {
  return <TabsPrimitive.Panel data-slot="tabs-content" className={cn("flex-1 outline-none", className)} {...props} />;
}

export { Tabs, TabsList, TabsTrigger, TabsContent, tabsListVariants };
