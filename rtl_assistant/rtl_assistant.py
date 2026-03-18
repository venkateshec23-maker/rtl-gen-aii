# rtl_assistant.py
"""RTL Assistant - Main Application"""

import os
import sys
from design_parser import DesignParser
from template_generator import TemplateGenerator
from file_manager import FileManager


class RTLAssistant:
    """Main application class"""

    def __init__(self):
        print("\n" + "=" * 60)
        print("🚀 RTL DESIGN ASSISTANT")
        print("=" * 60)

        self.parser = DesignParser()
        self.generator = TemplateGenerator()
        self.files = FileManager()
        self.config = self.files.load_config()

        print("✓ Loaded configuration")
        print("✓ Ready to generate designs")

    def run(self):
        """Main application loop"""
        while True:
            self.show_menu()
            choice = input("\nChoice: ").strip()

            if choice == "1":
                self.create_design()
            elif choice == "2":
                self.view_history()
            elif choice == "3":
                self.show_stats()
            elif choice == "4":
                self.configure()
            elif choice == "5":
                self.exit_app()
                break
            else:
                print("❌ Invalid choice. Try again.")

    def show_menu(self):
        print("\n" + "-" * 40)
        print("MAIN MENU")
        print("-" * 40)
        print("1. ✏️  Create New Design")
        print("2. 📋 View Design History")
        print("3. 📊 Show Statistics")
        print("4. ⚙️  Configuration")
        print("5. 🚪 Exit")
        print("-" * 40)

    def create_design(self):
        print("\n" + "-" * 40)
        print("CREATE NEW DESIGN")
        print("-" * 40)
        print("Describe your design (or 'back' to return)")
        print("Example: 'Create an 8-bit adder with clock'")

        description = input("\nDescription: ").strip()

        if description.lower() == 'back':
            return
        if not description:
            print("❌ Description cannot be empty")
            return

        print("\n🔍 Parsing description...")
        parsed = self.parser.parse(description)

        print("\n📋 Parsed Information:")
        print(f"  Component: {parsed['component']}")
        print(f"  Bit Width: {parsed['bit_width']}")
        print(f"  Has Clock: {parsed['has_clock']}")
        print(f"  Has Reset: {parsed['has_reset']}")
        if parsed['operations']:
            print(f"  Operations: {', '.join(parsed['operations'])}")
        print(f"  Confidence: {parsed['confidence']:.1%}")

        module_name = self.parser.suggest_module_name(parsed)
        parsed['module_name'] = module_name
        print(f"\n💡 Suggested module name: {module_name}")

        confirm = input("\nGenerate this design? (y/n): ").lower()
        if confirm != 'y':
            print("❌ Design cancelled")
            return

        print("\n⚙️ Generating Verilog code...")
        code = self.generator.generate(parsed)

        print("\n📄 Generated Code Preview:")
        print("-" * 40)
        preview_lines = code.split('\n')[:10]
        for line in preview_lines:
            print(line)
        print("...")
        print("-" * 40)

        save = input("\n💾 Save design? (y/n): ").lower()
        if save == 'y':
            try:
                design_dir = self.files.save_design(parsed, code)
                print(f"✅ Design saved to: {design_dir}")
                self.files.log_activity("CREATE", f"{module_name} - {description[:30]}")
            except Exception as e:
                print(f"❌ Error saving: {e}")
        else:
            print("❌ Design not saved")

    def view_history(self):
        print("\n" + "-" * 40)
        print("DESIGN HISTORY")
        print("-" * 40)

        history = self.files.get_history()

        if not history:
            print("No designs yet. Create one first!")
            return

        for i, entry in enumerate(reversed(history), 1):
            print(f"\n{i}. {entry['module_name']}")
            print(f"   📅 {entry['timestamp'][:19]}")
            print(f"   🔧 {entry['component']}, {entry['bit_width']}bit")
            print(f"   📝 {entry['description']}")

        input("\nPress Enter to continue...")

    def show_stats(self):
        print("\n" + "-" * 40)
        print("STATISTICS")
        print("-" * 40)

        history = self.files.get_history()

        if not history:
            print("No data yet")
            return

        components = {}
        widths = {}

        for entry in history:
            comp = entry.get('component', 'unknown')
            width = entry.get('bit_width', 0)
            components[comp] = components.get(comp, 0) + 1
            widths[width] = widths.get(width, 0) + 1

        print(f"\nTotal Designs: {len(history)}")
        print("\nBy Component:")
        for comp, count in sorted(components.items()):
            print(f"  {comp}: {count}")
        print("\nBy Bit Width:")
        for width, count in sorted(widths.items()):
            print(f"  {width}-bit: {count}")

    def configure(self):
        print("\n" + "-" * 40)
        print("CONFIGURATION")
        print("-" * 40)
        print("Current settings:")
        for key, value in self.config.items():
            print(f"  {key}: {value}")
        print("\nEdit config in: config.json")
        input("\nPress Enter to continue...")

    def exit_app(self):
        print("\n" + "=" * 60)
        print("👋 Thank you for using RTL Assistant!")
        print("=" * 60)


if __name__ == "__main__":
    try:
        app = RTLAssistant()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
