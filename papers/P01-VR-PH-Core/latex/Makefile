# Makefile for P01 LaTeX build
# Usage:
#   make          — build PDF
#   make clean    — remove build artifacts
#   make arxiv    — create arXiv submission tarball

TEX    = main
LATEX  = pdflatex
BIBTEX = bibtex

.PHONY: all clean arxiv watch

all: $(TEX).pdf

$(TEX).pdf: $(TEX).tex references.bib
	$(LATEX) $(TEX)
	$(BIBTEX) $(TEX)
	$(LATEX) $(TEX)
	$(LATEX) $(TEX)

# Use latexmk for continuous builds
watch:
	latexmk -pdf -pvc $(TEX).tex

clean:
	rm -f $(TEX).{aux,bbl,blg,log,out,toc,pdf,fls,fdb_latexmk,synctex.gz}
	rm -f *.aux

# Create arXiv-compatible tarball
# arXiv requires: .tex, .bbl (not .bib), figures/, and any .sty files
arxiv: $(TEX).pdf
	@echo "Creating arXiv submission..."
	@mkdir -p arxiv-submit
	cp $(TEX).tex arxiv-submit/
	cp $(TEX).bbl arxiv-submit/
	@if [ -d figures ] && [ "$$(ls -A figures 2>/dev/null)" ]; then \
		cp -r figures/ arxiv-submit/figures/; \
	fi
	cd arxiv-submit && tar czf ../$(TEX)-arxiv.tar.gz *
	@rm -rf arxiv-submit
	@echo "Created $(TEX)-arxiv.tar.gz"
	@echo "Upload this file to https://arxiv.org/submit"
