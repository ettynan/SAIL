/**
 * Reusable button component for SAIL Orbit.
 *
 * Renders a standard HTML button or delegates rendering to a child
 * element through Radix UI Slot.
 *
 * Applies shared CVA styling based on the selected variant and size.
 * Styling configuration is maintained in button-variants.js to
 * preserve compatibility with React Fast Refresh.
 */

import { cn } from "cn";
import { Slot } from "radix-ui";
import { buttonVariants } from "./button-variants";

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}) {
  // Use Radix Slot when another element must inherit button behavior
  // and styling; otherwise render a native HTML button.
  const Comp = asChild ? Slot.Root : "button";

  return (
    <Comp
      // Expose button configuration through data attributes for styling.
      data-slot="button"
      data-variant={variant}
      data-size={size}

      // Combine the selected CVA styles with any custom class names.
      className={cn(buttonVariants({ variant, size, className }))}

      // Forward remaining properties, including event handlers and accessibility attributes.
      {...props}
    />
  );
}

// Export only the React component to satisfy Fast Refresh requirements.
export { Button };