# Makefile for P03 LaTeX build
# Usage:
#   make          — build PDF
#   make clean    — remove build artifacts
#   make arxiv    — create arXiv submission tarball

TEX    = main
LATEX  = pdflatex
BIBTEX = bibtex

.PHONY: all clean arxiv watch figures

all: $(TEX).pdf

$(TEX).pdf: $(TEX).tex body.tex references.bib
	$(LATEX) $(TEX)
	$(BIBTEX) $(TEX)
	$(LATEX) $(TEX)
	$(LATEX) $(TEX)

# Use latexmk for continuous builds
watch:
	latexmk -pdf -pvc $(TEX).tex

# Copy figures from papers/P03-Zigzag/figures/ into latex/figures/
figures:
	mkdir -p figures
	cp ../figures/*.pdf figures/ 2>/dev/null || true
	cp ../figures/*.png figures/ 2>/dev/null || true

clean:
	rm -f $(TEX).{aux,bbl,blg,log,out,toc,pdf,fls,fdb_latexmk,synctex.gz}
	rm -f *.aux

# Create arXiv-compatible tarball (uses .bbl, not .bib)
arxiv: $(TEX).pdf
	mkdir -p arxiv_submission
	cp $(TEX).tex body.tex $(TEX).bbl arxiv_submission/
	cp -r figures/ arxiv_submission/figures/
	cd arxiv_submission && tar czf ../p03-zigzag-arxiv.tar.gz .
	rm -rf arxiv_submission
	@echo "arXiv tarball: p03-zigzag-arxiv.tar.gz"
