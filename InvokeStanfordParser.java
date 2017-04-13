import java.io.*;
import java.util.*;
import edu.stanford.nlp.trees.*;
import edu.stanford.nlp.parser.lexparser.LexicalizedParser;
import edu.stanford.nlp.parser.lexparser.TestOptions;
//originally import edu.stanford.nlp.parser.lexparser.Test;

class InvokeStanfordParser {
    public static void main(String[] args) {
	LexicalizedParser lp= LexicalizedParser.loadModel("edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz");	
	lp.setOptionFlags(new String[]{"-maxLength", "80","-retainTmpSubcategories"});
	//TestOptions.MAX_ITEMS = 1000000;,"-outputFormatOptions","\"nonCollapsedDependencies\""
	System.out.println("Loading done!");
	System.err.println("DEBUG PARSER loaded parser model.");

	try {
	    PrintWriter pw = new PrintWriter(System.out);

	    BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
	    String sent = in.readLine();
	    String[] split = null;
	    if (sent != null) {
		System.err.println("DEBUG PARSER got line: " + sent);
		split = sent.split("\\s+");
		System.err.println("DEBUG PARSER first split size: " + split.length);
	    }
	    while (sent != null && split.length < 2) {
		sent = in.readLine();
		split = sent.split("\\s+");
		System.err.println("DEBUG PARSER got line: " + sent);
	    }
	    System.err.println("DEBUG PARSER received sentence.");
	    while (sent != null) {

		Tree parse = (Tree) lp.apply(sent);
		//parse.pennPrint();
		//System.out.println();

		TreebankLanguagePack tlp = new PennTreebankLanguagePack();
		//GrammaticalStructureFactory gsf = tlp.grammaticalStructureFactory();
		//GrammaticalStructure gs = gsf.newGrammaticalStructure(parse);
		//Collection tdl = gs.typedDependencies();
		//System.out.println(tdl);
		//System.out.println();

		TreePrint tp = new TreePrint("wordsAndTags,typedDependencies","nonCollapsedDependencies",tlp);
		//,"nonCollapsedDependencies",tlp
		
		System.out.println("!@!@");
		System.out.flush();
		System.err.println("DEBUG PARSER this is the first symbol.");
		tp.printTree(parse, pw);
		System.err.println("DEBUG PARSER printed parse.");
		pw.flush();
		System.err.println("DEBUG PARSER flushed parse.");
		System.out.flush();
		System.out.println("####");
		System.out.flush();
		System.err.println("DEBUG PARSER printed second symbol.");

		sent = in.readLine();
		System.out.println(sent);
		if (sent != null) {
		    split = sent.split("\\s+");
		    System.err.println("DEBUG PARSER got line: " + sent);
		}
		while (sent != null && split.length < 2) {
		    sent = in.readLine();
		    split = sent.split("\\s+");
		    System.err.println("DEBUG PARSER got line: " + sent);
		}

		System.err.println("DEBUG PARSER received subsequent sentence.");
	    }
	} catch (IOException ioe) {
	}
    }
}
