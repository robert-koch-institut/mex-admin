import reflex as rx

MEX_LOGO_ANIMATED_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" class="mex-logo" width="66" height="25"
     viewBox="0 0 66 25" role="img" aria-label="MEx - Metadata Exchange">
  <title>MEx - Metadata Exchange</title>
  <style>
    .mex-logo { color: #000080; }

    .mex-logo .mex-seg {
      fill: none;
      stroke: var(--mex-logo-ink, currentColor);
      stroke-width: 1.84;
      stroke-linecap: butt;
      stroke-linejoin: round;
      stroke-dasharray: 1 1;
      stroke-dashoffset: 0;
    }

    @media (prefers-reduced-motion: no-preference) {
      .mex-logo .mex-seg {
        animation-name: mex-logo-draw;
        animation-timing-function: linear;
        animation-fill-mode: both;
      }
      .mex-logo .mex-s1 { animation-duration: 0.35s; animation-delay: 0.0s; }
      .mex-logo .mex-s2 { animation-duration: 0.28s; animation-delay: 0.31s; }
      .mex-logo .mex-s3 { animation-duration: 0.38s; animation-delay: 0.55s; }
      .mex-logo .mex-s4 { animation-duration: 0.20s; animation-delay: 0.89s; }
    }

    @keyframes mex-logo-draw {
      from { stroke-dashoffset: 1; }
      to   { stroke-dashoffset: 0; }
    }
  </style>

  <defs>
    <clipPath id="mex-logo-tip3">
      <path d="M-4 -4H60 V12.4773 H72 V29 H-4 Z"/>
    </clipPath>
    <clipPath id="mex-logo-tip4">
      <rect x="-4" y="12.4775" width="76" height="11.9954"/>
    </clipPath>
  </defs>

  <path class="mex-seg mex-s1" pathLength="1"
        d="M0.925 24.47L0.925 8.451A7.117 7.117 0 0 1 15.159 8.451L15.159 24.47"/>
  <path class="mex-seg mex-s2" pathLength="1"
        d="M15.02 6.936A7.437 7.437 0 0 1 28.913 5.603C29.686 7.21 30.7 8.69 31.561
           10.251C32.402 11.778 33.485 13.324 34.997 14.192C36.496 15.053 38.486
           15.194 40.154 14.739L48.473 12.465"/>
  <path class="mex-seg mex-s3" pathLength="1" clip-path="url(#mex-logo-tip3)"
        d="M52.522 2.23A11.045 11.045 0 1 0 54.044 22.038C54.904 21.535 55.735
           20.964 56.481 20.302C57.226 19.641 57.822 18.829 58.483 18.084L64.08
           11.777"/>
  <path class="mex-seg mex-s4" pathLength="1" clip-path="url(#mex-logo-tip4)"
        d="M54.149 11.797L65.263 25.154"/>
</svg>
"""


def animated_mex_logo(width: str = "calc(200px * var(--scaling))") -> rx.Component:
    """Return the animated MEx logo that draws its strokes on mount.

    Args:
        width: CSS width of the logo, the height follows the aspect ratio
    """
    return rx.box(
        rx.html(MEX_LOGO_ANIMATED_SVG),
        custom_attrs={"data-testid": "mex-logo"},
        style=rx.Style(
            {
                "--mex-logo-ink": rx.color("accent", 11),
                "width": width,
                "maxWidth": "100%",
                "& svg": {
                    "display": "block",
                    "height": "auto",
                    "width": "100%",
                },
            }
        ),
    )
