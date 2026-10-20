function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatSimilarity(value) {
  return Number(value).toFixed(3);
}

function insightCard(label, value, description, reference = null) {
  const card = element('article', 'insight-card');
  card.append(element('div', 'result-label', label), element('h3', '', value), element('p', '', description));
  if (reference) {
    const scale = element('div', 'reference-scale');
    const track = element('div', 'reference-track');
    const marker = element('span', 'reference-marker');
    const benchmark = element('span', 'reference-benchmark');
    const position = Math.max(0, Math.min(100, ((reference.value + 1) / 2) * 100));
    const benchmarkPosition = Math.max(0, Math.min(100, ((reference.benchmark + 1) / 2) * 100));
    marker.style.left = `${position}%`;
    benchmark.style.left = `${benchmarkPosition}%`;
    track.append(marker, benchmark);
    const key = element('div', 'reference-key');
    key.append(element('span', '', '−1'), element('span', '', 'Your score · positive-reference marker'), element('span', '', '+1'));
    scale.append(track, key);
    card.append(scale);
  }
  return card;
}

function detailsSection(result) {
  const section = element('section', 'result-panel details-section');
  const heading = element('div', 'section-heading');
  heading.append(element('h2', '', 'Understand the results'), element('p', '', 'Open any topic for technical context and limitations.'));
  section.append(heading);
  const topics = [
    ['Skin-type scores', 'The three numbers are softmax model scores for provisional Dry, Normal, and Oily image classes. They sum to approximately one, but they are not calibrated probabilities or measurements of skin physiology.'],
    ['Positive-reference similarity', 'The acne and dark-circle values are cosine similarities between this image embedding and fitted positive-reference embeddings. A higher value means closer representation-space similarity; it does not establish presence, absence, severity, or diagnosis.'],
    ['Age-like estimate', 'This is a regression estimate of an unresolved historical numeric dataset label. It is not verified chronological age, biological age, or medically validated skin age.'],
    ['Automatic face crop', 'Every fitted component receives the same automatically detected facial crop. Cropping changes the fitted input distribution because the existing models were developed largely with full-image preprocessing; it has not been shown to improve accuracy.'],
    ['Photography and bias', 'Lighting, framing, blur, camera processing, cosmetics, occlusion, skin tone, and differences from the fitted data can all change outputs. The development data was not an independent clinical test set.'],
  ];
  const warnings = result.review.quality.warnings || [];
  if (warnings.length) {
    topics.push([
      'Photo quality notes',
      `${warnings.map((warning) => `${warning.title}: ${warning.message}`).join(' ')} These are deterministic technical heuristics, not clinical image-quality grading.`,
    ]);
  }
  topics.forEach(([title, copy]) => {
    const details = document.createElement('details');
    details.append(element('summary', '', title), element('div', 'details-content', copy));
    section.append(details);
  });
  const technical = document.createElement('details');
  const grid = element('div', 'technical-grid');
  const values = [
    ['Model family', 'ResNet50'],
    ['Processing', 'Automatic face crop'],
    ['Source dimensions', result.review.source.dimensions.join(' × ')],
    ['Face detection', result.review.face_detection.status.replaceAll('_', ' ')],
    ['Analyzed crop', result.crop_dimensions.join(' × ')],
    ['Crop used', 'Yes · experimental distribution change'],
    ['Local duration', `${Math.round(result.inference_duration_ms)} ms`],
    ['Model version', result.primary.model_version],
    ['EXIF adjusted', result.review.source.exif_orientation_applied ? 'Yes' : 'No'],
    ['Photo persisted', 'No'],
  ];
  values.forEach(([label, value]) => {
    const item = element('div');
    item.append(element('span', '', label), element('strong', '', value));
    grid.append(item);
  });
  technical.append(element('summary', '', 'Technical details'), grid);
  section.append(technical);
  return section;
}

export function renderResults(mount, result, onNewAnalysis) {
  mount.replaceChildren();
  const header = element('div', 'results-header');
  const headerText = element('div');
  headerText.append(element('p', 'kicker', 'ANALYSIS COMPLETE'), element('h1', '', 'Your experimental report'), element('p', '', 'A transparent view of what the local models returned from the detected facial region.'));
  const newButton = element('button', 'button button-secondary', 'Analyze another photo');
  newButton.type = 'button';
  newButton.addEventListener('click', onNewAnalysis);
  header.append(headerText, newButton);

  const overview = element('section', 'overview-strip');
  const thumbnail = document.createElement('img');
  thumbnail.src = result.crop_preview;
  thumbnail.alt = 'Analyzed facial region used for every model output';
  const summary = element('div');
  summary.append(element('strong', '', 'Analyzed facial region'), element('span', '', 'Automatically cropped · Processed locally · Image not retained'));
  const duration = element('span', 'model-chip', `${Math.round(result.inference_duration_ms)} ms local`);
  overview.append(thumbnail, summary, duration);

  const reportGrid = element('div', 'report-grid');
  const skinPanel = element('section', 'result-panel skin-primary');
  skinPanel.append(element('div', 'result-label', 'PRIMARY RESULT · PROVISIONAL IMAGE CLASS'));
  const skinResult = element('div', 'skin-result');
  skinResult.append(element('h2', '', result.primary.skin_type.label), element('span', 'model-chip', 'ResNet50'));
  skinPanel.append(skinResult);
  const scores = element('div', 'score-stack');
  Object.entries(result.primary.skin_type.scores).forEach(([name, score]) => {
    const row = element('div', 'score-row');
    const track = element('div', 'score-track');
    const fill = element('span', 'score-fill');
    fill.style.width = `${Math.max(0, Math.min(100, Number(score) * 100))}%`;
    track.append(fill);
    row.append(element('span', '', name), track, element('span', 'score-number', formatPercent(score)));
    scores.append(row);
  });
  skinPanel.append(scores, element('p', 'explanation', 'The highlighted class has the largest model score. These values are not calibrated confidence and do not objectively measure dry, normal, or oily skin physiology.'));

  const insights = element('div', 'insight-stack');
  insights.append(
    insightCard('EXPERIMENTAL AGE-LIKE TARGET', `${result.primary.age_like_numeric_target}`, 'Historical label units—not the person’s actual or biological age.'),
    insightCard('ACNE POSITIVE-REFERENCE SIMILARITY', formatSimilarity(result.primary.positive_references.acne.similarity), 'Embedding closeness to fitted positive references. Not a Yes/No detector.', { value: result.primary.positive_references.acne.similarity, benchmark: result.primary.positive_references.acne.positive_reference_p10 }),
    insightCard('DARK-CIRCLE POSITIVE-REFERENCE SIMILARITY', formatSimilarity(result.primary.positive_references.dark_circle.similarity), 'Embedding closeness to fitted positive references. Not a condition probability.', { value: result.primary.positive_references.dark_circle.similarity, benchmark: result.primary.positive_references.dark_circle.positive_reference_p10 }),
  );
  reportGrid.append(skinPanel, insights);

  mount.append(header, overview, reportGrid);
  mount.append(detailsSection(result));
  mount.append(element('aside', 'results-disclaimer', 'Research limitation: these fitted components use provisional labels and have no independent clinical validation. Acne and dark-circle references lack verified negatives. Do not use this report for diagnosis, treatment, skincare purchasing, identity inference, or decisions about a person.'));
}
