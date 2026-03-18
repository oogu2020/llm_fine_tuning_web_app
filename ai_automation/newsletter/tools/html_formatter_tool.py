#!/usr/bin/env python3
"""
HTML formatter tool for newsletter automation.
Converts curated content into visually stimulating HTML newsletter.
"""

import json
import os
import sys
import datetime
from typing import Dict, List, Any

def format_newsletter(curated_file: str, topic: str, issue_date: str = None,
                      style_preference: str = "modern", include_toc: bool = True,
                      branding_logo: str = None, primary_color: str = None,
                      secondary_color: str = None, font_family: str = None) -> Dict[str, Any]:
    """
    Format curated content into HTML newsletter.

    Args:
        curated_file: Path to JSON file containing curated content
        topic: The newsletter topic
        issue_date: Publication date (YYYY-MM-DD), defaults to today
        style_preference: Design style (modern, classic, minimal, vibrant)
        include_toc: Whether to include table of contents
        branding_logo: Path to logo image file (optional)
        primary_color: Primary brand color (hex format, optional)
        secondary_color: Secondary brand color (hex format, optional)
        font_family: Font family for headings (optional)

    Returns:
        Dictionary containing formatting results and file path
    """

    # Validate inputs
    if not os.path.exists(curated_file):
        raise FileNotFoundError(f"Curated file not found: {curated_file}")

    if not topic or not topic.strip():
        raise ValueError("Topic must be provided")

    # Set issue date
    if issue_date is None:
        issue_date = datetime.datetime.now().strftime("%Y-%m-%d")
    else:
        # Validate date format
        try:
            datetime.datetime.strptime(issue_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("issue_date must be in YYYY-MM-DD format")

    # Load curated content
    with open(curated_file, 'r', encoding='utf-8') as f:
        curated_data = json.load(f)

    # Generate HTML newsletter
    html_content = generate_html_newsletter(
        curated_data, topic, issue_date, style_preference, include_toc
    )

    # Create output structure
    output = {
        "topic": topic,
        "formatting_date": datetime.datetime.now().isoformat(),
        "issue_date": issue_date,
        "style_preference": style_preference,
        "include_toc": include_toc,
        "word_count": curated_data.get('estimated_word_count', 0),
        "sections_count": len(curated_data.get('sections', [])),
        "html_content": html_content,
        "css_styles": get_css_styles(style_preference)
    }

    return output

def generate_html_newsletter(curated_data: Dict[str, Any], topic: str,
                           issue_date: str, style_preference: str, include_toc: bool) -> str:
    """Generate the complete HTML newsletter."""

    # Get CSS styles
    css_styles = get_css_styles(style_preference)

    # Start building HTML
    html_parts = []

    # HTML doctype and head
    html_parts.append('<!DOCTYPE html>')
    html_parts.append('<html lang="en">')
    html_parts.append('<head>')
    html_parts.append('    <meta charset="UTF-8">')
    html_parts.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append(f'    <title>{topic} - Newsletter Issue {issue_date}</title>')
    html_parts.append('    <style>')
    html_parts.append(css_styles)
    html_parts.append('    </style>')
    html_parts.append('</head>')
    html_parts.append('<body>')

    # Container
    html_parts.append('    <div class="newsletter-container">')

    # Header
    html_parts.append('        <header class="newsletter-header">')
    html_parts.append(f'            <h1 class="newsletter-title">{topic}</h1>')
    html_parts.append(f'            <p class="newsletter-date">Issue Date: {issue_date}</p>')
    html_parts.append('        </header>')

    # Table of Contents (if requested)
    if include_toc and len(curated_data.get('sections', [])) > 1:
        html_parts.append('        <nav class="toc">')
        html_parts.append('            <h2>Table of Contents</h2>')
        html_parts.append('            <ul>')
        for i, section in enumerate(curated_data.get('sections', [])):
            anchor = section["heading"].lower().replace(' ', '-').replace('&', 'and')
            html_parts.append(f'                <li><a href="#{anchor}">{section["heading"]}</a></li>')
        html_parts.append('            </ul>')
        html_parts.append('        </nav>')

    # Main content sections
    html_parts.append('        <main class="newsletter-content">')

    for i, section in enumerate(curated_data.get('sections', [])):
        html_parts.append(f'            <section class="newsletter-section" id="{section["heading"].lower().replace(" ", "-").replace("&", "and")}">')
        html_parts.append(f'                <h2 class="section-heading">{section["heading"]}</h2>')

        # Section summary/intro
        if section.get('summary'):
            html_parts.append(f'                <p class="section-summary">{section["summary"]}</p>')

        # Items in section
        items = section.get('items', [])
        if items:
            html_parts.append('                <div class="section-items">')
            for j, item in enumerate(items):
                html_parts.append('                    <div class="newsletter-item">')
                html_parts.append(f'                        <h3 class="item-title">{item.get("title", "Untitled")}</h3>')
                html_parts.append(f'                        <p class="item-source">Source: {item.get("source", "Unknown Source")}</p>')

                # Processed summary or key points
                if item.get('processed_summary'):
                    html_parts.append(f'                        <p class="item-summary">{item["processed_summary"]}</p>')
                elif item.get('key_points'):
                    html_parts.append('                        <ul class="item-key-points">')
                    for point in item['key_points']:
                        html_parts.append(f'                            <li>{point}</li>')
                    html_parts.append('                        </ul>')

                # Placeholder for image/infographic
                html_parts.append('                        <div class="image-placeholder">')
                html_parts.append('                            <p>[Image/Infographic Placeholder]</p>')
                html_parts.append('                        </div>')

                # Read more link
                if item.get('url'):
                    html_parts.append(f'                        <a href="{item["url"]}" class="read-more" target="_blank">Read more →</a>')

                html_parts.append('                    </div>')
            html_parts.append('                </div>')

        html_parts.append('            </section>')

    html_parts.append('        </main>')

    # Footer
    html_parts.append('        <footer class="newsletter-footer">')
    html_parts.append('            <p>© ' + str(datetime.datetime.now().year) + ' Newsletter Automation. All rights reserved.</p>')
    html_parts.append('            <p class="footer-note">This newsletter was generated automatically. Content sourced from various references.</p>')
    html_parts.append('            <div class="footer-links">')
    html_parts.append('                <a href="#" class="footer-link">Unsubscribe</a> | ')
    html_parts.append('                <a href="#" class="footer-link">View Archive</a> | ')
    html_parts.append('                <a href="#" class="footer-link">Forward to Friend</a>')
    html_parts.append('            </div>')
    html_parts.append('        </footer>')

    html_parts.append('    </div>')  # Close container
    html_parts.append('</body>')
    html_parts.append('</html>')

    return '\n'.join(html_parts)

def get_css_styles(style_preference: str, primary_color: str = None, secondary_color: str = None, font_family: str = None) -> str:
    """Get CSS styles based on preference with optional branding customization."""

    # Set default colors and fonts
    if primary_color is None:
        primary_color = "#3498db"  # Default blue
    if secondary_color is None:
        secondary_color = "#2c3e50"  # Default dark blue
    if font_family is None:
        font_family = "'Georgia', 'Times New Roman', serif"  # Default font

    base_styles = f"""
        /* Base Styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: {font_family};
            line-height: 1.6;
            color: #333;
            background-color: #f9f9f9;
        }}

        .newsletter-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .newsletter-header {{
            text-align: center;
            padding: 30px 20px;
            border-bottom: 1px solid #eee;
        }}

        .newsletter-title {{
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 10px;
            color: {secondary_color};
        }}

        .newsletter-date {{
            font-size: 16px;
            color: #7f8c8d;
            font-style: italic;
        }}

        .newsletter-section {{
            padding: 25px 20px;
            border-bottom: 1px solid #f0f0f0;
        }}

        .section-heading {{
            font-size: 22px;
            margin-bottom: 15px;
            color: {secondary_color};
            border-left: 4px solid {primary_color};
            padding-left: 10px;
        }}

        .section-summary {{
            font-size: 16px;
            margin-bottom: 20px;
            color: #555;
            font-style: italic;
        }}

        .newsletter-item {{
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px dashed #eee;
        }}

        .item-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
            color: {secondary_color};
        }}

        .item-source {{
            font-size: 12px;
            color: #95a5a6;
            margin-bottom: 8px;
            font-style: italic;
        }}

        .item-summary {{
            font-size: 14px;
            margin-bottom: 12px;
            line-height: 1.5;
        }}

        .item-key-points {{
            margin-bottom: 12px;
            padding-left: 20px;
        }}

        .item-key-points li {{
            margin-bottom: 6px;
            position: relative;
        }}

        .item-key-points li:before {{
            content: "•";
            color: {primary_color};
            font-weight: bold;
            display: inline-block;
            width: 1em;
            margin-left: -1em;
        }}

        .image-placeholder {{
            background-color: #ecf0f1;
            border: 2px dashed #bdc3c7;
            text-align: center;
            padding: 20px;
            margin: 15px 0;
            font-size: 14px;
            color: #7f8c8d;
            font-style: italic;
        }}

        .read-more {{
            display: inline-block;
            padding: 6px 12px;
            background-color: {primary_color};
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 13px;
            margin-top: 10px;
        }}

        .read-more:hover {{
            background-color: #2980b9;
        }}

        .toc {{
            background-color: #f8f9fa;
            padding: 20px;
            margin-bottom: 25px;
            border-left: 3px solid {primary_color};
        }}

        .toc h2 {{
            font-size: 20px;
            margin-bottom: 15px;
            color: {secondary_color};
        }}

        .toc ul {{
            list-style-type: none;
        }}

        .toc li {{
            margin-bottom: 8px;
        }}

        .toc li a {{
            text-decoration: none;
            color: {primary_color};
            font-weight: 500;
        }}

        .toc li a:hover {{
            text-decoration: underline;
        }}

        .newsletter-footer {{
            text-align: center;
            padding: 25px 20px;
            border-top: 1px solid #eee;
            font-size: 14px;
            color: #95a5a6;
        }}

        .footer-note {{
            font-style: italic;
            margin-bottom: 15px;
        }}

        .footer-links a {{
            color: #95a5a6;
            text-decoration: none;
            margin: 0 5px;
        }}

        .footer-links a:hover {{
            text-decoration: underline;
        }}

        /* Responsive design */
        @media (max-width: 480px) {{
            .newsletter-container {{
                margin: 0;
                border-radius: 0;
            }}

            .newsletter-header {{
                padding: 20px 15px;
            }}

            .newsletter-title {{
                font-size: 24px;
            }}

            .newsletter-section {{
                padding: 20px 15px;
            }}

            .section-heading {{
                font-size: 20px;
            }}
        }}
    """

    # Style variations
    if style_preference == "classic":
        # Serif fonts, traditional layout
        return base_styles.replace(
            f"font-family: {font_family};",
            "font-family: 'Times New Roman', Times, serif;"
        ).replace(
            primary_color, "#8B4513"  # Saddle brown instead of blue
        ).replace(
            secondary_color, "#2F4F4F"  # Dark slate gray
        ).replace(
            "#34495e", "#4B0082"  # Indigo
        )

    elif style_preference == "minimal":
        # Ultra clean, lots of whitespace, limited colors
        minimal_styles = f"""
            /* Minimal Styles */
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                line-height: 1.7;
                color: #222;
                background-color: #fafafa;
            }}

            .newsletter-container {{
                max-width: 500px;
                margin: 0 auto;
                background-color: white;
            }}

            .newsletter-header {{
                text-align: center;
                padding: 40px 30px;
                border-bottom: 1px solid #eee;
            }}

            .newsletter-title {{
                font-size: 26px;
                font-weight: 300;
                letter-spacing: -0.5px;
                margin-bottom: 15px;
                color: #111;
            }}

            .newsletter-date {{
                font-size: 15px;
                color: #666;
            }}

            .newsletter-section {{
                padding: 35px 30px;
                border-bottom: 1px solid #fafafa;
            }}

            .section-heading {{
                font-size: 20px;
                margin-bottom: 20px;
                color: #222;
                border-bottom: 1px solid #eee;
                padding-bottom: 8px;
                letter-spacing: -0.3px;
            }}

            .section-summary {{
                font-size: 16px;
                margin-bottom: 25px;
                color: #555;
            }}

            .newsletter-item {{
                margin-bottom: 30px;
                padding-bottom: 20px;
            }}

            .item-title {{
                font-size: 17px;
                font-weight: 400;
                margin-bottom: 10px;
                color: #222;
            }}

            .item-source {{
                font-size: 12px;
                color: #888;
                margin-bottom: 8px;
            }}

            .item-summary {{
                font-size: 15px;
                margin-bottom: 15px;
                line-height: 1.6;
            }}

            .item-key-points {{
                margin-bottom: 15px;
            }}

            .item-key-points li {{
                margin-bottom: 8px;
                padding-left: 18px;
                position: relative;
            }}

            .item-key-points li:before {{
                content: "▸";
                color: #666;
                font-weight: 300;
                position: absolute;
                left: 0;
                top: 0;
            }}

            .image-placeholder {{
                background-color: #fafafa;
                border: 1px solid #eee;
                text-align: center;
                padding: 25px;
                margin: 20px 0;
                font-size: 14px;
                color: #999;
            }}

            .read-more {{
                display: inline-block;
                padding: 8px 16px;
                background-color: transparent;
                color: #222;
                text-decoration: none;
                border: 1px solid #222;
                border-radius: 0;
                font-size: 13px;
                margin-top: 12px;
                letter-spacing: 0.5px;
            }}

            .read-more:hover {{
                background-color: #f0f0f0;
            }}

            .toc {{
                background-color: #fafafa;
                padding: 25px 20px;
                margin-bottom: 30px;
                border-left: 2px solid #ddd;
            }}

            .toc h2 {{
                font-size: 18px;
                margin-bottom: 20px;
                color: #222;
            }}

            .toc li {{
                margin-bottom: 10px;
            }}

            .toc li a {{
                color: #555;
            }}

            .toc li a:hover {{
                color: #222;
            }}

            .newsletter-footer {{
                text-align: center;
                padding: 35px 30px;
                border-top: 1px solid #eee;
                font-size: 13px;
                color: #777;
            }}

            .footer-note {{
                color: #999;
            }}

            .footer-links a {{
                color: #777;
            }}

            .footer-links a:hover {{
                color: #555;
            }}

            @media (max-width: 480px) {{
                .newsletter-container {{
                    margin: 0;
                }}

                .newsletter-header {{
                    padding: 30px 20px;
                }}

                .newsletter-title {{
                    font-size: 22px;
                }}

                .newsletter-section {{
                    padding: 25px 20px;
                }}

                .section-heading {{
                    font-size: 18px;
                }}
            }}
        """
        return minimal_styles

    elif style_preference == "vibrant":
        # Bold colors, dynamic layouts
        return base_styles.replace(
            primary_color, "#e74c3c"  # Vibrant red
        ).replace(
            secondary_color, "#c0392b"  # Dark red
        ).replace(
            "#34495e", "#d35400"  # Orange
        ).replace(
            ".newsletter-container {", ".newsletter-container {\n            border-top: 5px solid #e74c3c;"
        ).replace(
            ".newsletter-header {", ".newsletter-header {\n            background: linear-gradient(135deg, #fadbd8 0%, #f5b7b1 100%);"
        )

    else:  # modern (default)
        return base_styles

def save_html_newsletter(results: Dict[str, Any], topic: str) -> str:
    """Save HTML newsletter to a file in .tmp directory."""
    # Create .tmp directory if it doesn't exist
    tmp_dir = os.path.join(os.path.dirname(__file__), '..', '.tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    # Create filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean topic for filename
    clean_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
    clean_topic = clean_topic.replace(' ', '_')
    filename = f"newsletter_{clean_topic}_{timestamp}.html"
    filepath = os.path.join(tmp_dir, filename)

    # Write HTML to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(results['html_content'])

    return filepath

def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Format curated content into HTML newsletter')
    parser.add_argument('--curated-file', required=True, help='Path to curated JSON file')
    parser.add_argument('--topic', required=True, help='Newsletter topic')
    parser.add_argument('--issue-date', help='Issue date (YYYY-MM-DD)')
    parser.add_argument('--style', choices=['modern', 'classic', 'minimal', 'vibrant'], default='modern', help='Style preference')
    parser.add_argument('--branding-logo', help='Path to branding logo image file (optional)')
    parser.add_argument('--primary-color', help='Primary brand color in hex format (optional)')
    parser.add_argument('--secondary-color', help='Secondary brand color in hex format (optional)')
    parser.add_argument('--font-family', help='Font family for headings (optional)')
    parser.add_argument('--no-toc', action='store_true', help='Exclude table of contents')
    parser.add_argument('--output', help='Output file path (optional)')

    args = parser.parse_args()

    try:
        # Format the newsletter
        results = format_newsletter(
            args.curated_file,
            args.topic,
            args.issue_date,
            args.style,
            not args.no_toc,  # include_toc is True unless --no-toc is specified
            args.branding_logo,
            args.primary_color,
            args.secondary_color,
            args.font_family
        )

        # Save to file
        output_path = save_html_newsletter(results, args.topic)

        # Print summary
        print(f"Newsletter formatting completed successfully!")
        print(f"Topic: {args.topic}")
        print(f"Issue date: {results['issue_date']}")
        print(f"Style: {args.style}")
        print(f"Includes TOC: {not args.no_toc}")
        print(f"Word count: {results['word_count']}")
        print(f"Sections: {results['sections_count']}")
        print(f"HTML saved to: {output_path}")

        # If output path specified, also save there
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(results['html_content'])
            print(f"Also saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"Error during formatting: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    exit(main())