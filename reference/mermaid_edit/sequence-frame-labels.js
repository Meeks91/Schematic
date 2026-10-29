// Renders Mermaid sequence control frames as English, after mermaid.render():
//   alt [x]  -> "IF x"   ·   else [y] -> "ELSE y"   ·   opt [z] -> "IF ONLY z"   ·   loop [w] -> "LOOP w"
// The .mmd stays standard Mermaid; only the rendered SVG changes, so plain viewers still show alt/opt.
(function () {
  const FRAME_KEYWORD_TO_LABEL = { alt: "IF", opt: "IF ONLY", loop: "LOOP" };
  const ELSE_LABEL = "ELSE";
  const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
  const LABEL_INSET_PX = 10;
  const LABEL_FONT_WEIGHT = "600";
  const LABEL_PLATE_PADDING_PX = 3;
  const LABEL_PLATE_RADIUS_PX = 3;
  const LABEL_PLATE_FILL = "#1e1e2e";
  const FRAME_COLOUR = "#89b4fa";
  const FRAME_DASH_PATTERN = "2, 3";

  function stripBrackets(text) {
    return text.trim().replace(/^\[/, "").replace(/\]$/, "");
  }

  function frameLeftX(tagBox) {
    return parseFloat(tagBox.getAttribute("points").split(",")[0]);
  }

  function placeAtFrameLeft(textElement, leftX) {
    textElement.setAttribute("text-anchor", "start");
    textElement.setAttribute("x", String(leftX + LABEL_INSET_PX));
    textElement.querySelectorAll("tspan").forEach(tspan => tspan.setAttribute("x", String(leftX + LABEL_INSET_PX)));
    textElement.style.fontWeight = LABEL_FONT_WEIGHT;
  }

  function backLabelWithPlate(textElement) {
    const bounds = textElement.getBBox();
    const plate = document.createElementNS(SVG_NAMESPACE, "rect");
    plate.setAttribute("x", String(bounds.x - LABEL_PLATE_PADDING_PX));
    plate.setAttribute("y", String(bounds.y - LABEL_PLATE_PADDING_PX));
    plate.setAttribute("width", String(bounds.width + 2 * LABEL_PLATE_PADDING_PX));
    plate.setAttribute("height", String(bounds.height + 2 * LABEL_PLATE_PADDING_PX));
    plate.setAttribute("rx", String(LABEL_PLATE_RADIUS_PX));
    plate.setAttribute("fill", LABEL_PLATE_FILL);
    plate.classList.add("frame-label-plate");
    textElement.parentNode.insertBefore(plate, textElement);
  }

  function colourFrame(frameGroup) {
    frameGroup.querySelectorAll(":scope > line.loopLine").forEach(line => {
      line.style.setProperty("stroke", FRAME_COLOUR, "important");
      line.style.setProperty("stroke-dasharray", FRAME_DASH_PATTERN, "important");
    });
    frameGroup.querySelectorAll(":scope > text.labelText, :scope > text.sectionTitle").forEach(labelText => {
      labelText.style.setProperty("fill", FRAME_COLOUR, "important");
    });
  }

  function relabelFrame(frameGroup) {
    const tagText = frameGroup.querySelector(":scope > text.labelText");
    const keyword = tagText && tagText.textContent.trim();
    const label = keyword && FRAME_KEYWORD_TO_LABEL[keyword];
    if (!label) return;
    const tagBox = frameGroup.querySelector(":scope > polygon.labelBox");
    const conditionText = frameGroup.querySelector(":scope > text.loopText");
    const leftX = frameLeftX(tagBox);
    const condition = conditionText ? stripBrackets(conditionText.textContent) : "";

    tagText.textContent = condition ? `${label} ${condition}` : label;
    tagText.removeAttribute("dominant-baseline");
    tagText.removeAttribute("alignment-baseline");
    tagText.setAttribute("y", conditionText ? conditionText.getAttribute("y") : tagText.getAttribute("y"));
    placeAtFrameLeft(tagText, leftX);
    if (conditionText) conditionText.remove();
    tagBox.remove();

    frameGroup.querySelectorAll(":scope > text.sectionTitle").forEach(elseText => {
      elseText.textContent = `${ELSE_LABEL} ${stripBrackets(elseText.textContent)}`;
      placeAtFrameLeft(elseText, leftX);
    });
    colourFrame(frameGroup);
  }

  window.relabelSequenceFrames = function relabelSequenceFrames(svgRoot) {
    const frameGroups = svgRoot.querySelectorAll('g[data-et="control-structure"]');
    frameGroups.forEach(relabelFrame);
    frameGroups.forEach(frameGroup => {
      const svgElement = frameGroup.ownerSVGElement;
      frameGroup.querySelectorAll(":scope > text.labelText, :scope > text.sectionTitle").forEach(labelText => {
        backLabelWithPlate(labelText);
        svgElement.appendChild(labelText.previousSibling);
        svgElement.appendChild(labelText);
      });
    });
  };
})();
