// Supplemental D4 experiment on fixed learned FSMs; no live UE or radio time.
import de.learnlib.acex.analyzers.AcexAnalyzers;
import de.learnlib.algorithms.ttt.mealy.TTTLearnerMealy;
import de.learnlib.api.oracle.MembershipOracle.MealyMembershipOracle;
import de.learnlib.api.query.Query;
import de.learnlib.api.query.DefaultQuery;
import de.learnlib.oracle.equivalence.CheckingEQOracle;
import de.learnlib.oracle.equivalence.MealyWpMethodEQOracle;
import net.automatalib.automata.transducers.MealyMachine;
import net.automatalib.words.Word;
import net.automatalib.words.WordBuilder;
import net.automatalib.words.impl.SimpleAlphabet;
import net.automatalib.serialization.dot.GraphDOT;
import java.nio.file.*;
import java.util.*;
import java.io.*;

public class OfflineD4 {
    static class Edge {String next, output; Edge(String n,String o){next=n;output=o;}}
    static class Oracle implements MealyMembershipOracle<String,String> {
        Map<String,Map<String,Edge>> target; long queries=0,symbols=0;
        Oracle(Map<String,Map<String,Edge>> t){target=t;}
        public void processQueries(Collection<? extends Query<String,Word<String>>> batch){
            for(Query<String,Word<String>> q:batch){
                queries++; Word<String> input=q.getInput(); symbols+=input.length();
                String state="s0";WordBuilder<String> output=new WordBuilder<>();
                for(String a:input){Edge e=target.get(state).get(a);if(e==null)throw new IllegalArgumentException("missing input "+a);output.append(e.output);state=e.next;}
                q.answer(output.toWord().subWord(q.getPrefix().length()));
            }
        }
    }
    public static void main(String[] args)throws Exception{
        Map<String,Map<String,Edge>> target=new HashMap<>();
        for(String line:Files.readAllLines(Paths.get(args[0]))){String[] f=line.split("\t");target.computeIfAbsent(f[0],s->new HashMap<>()).put(f[1],new Edge(f[2],f[3]));}
        List<String> inputs=Arrays.asList(Files.readString(Paths.get(args[1])).trim().split("\\s+"));
        SimpleAlphabet<String> alphabet=new SimpleAlphabet<>(inputs);
        List<Word<String>> pces=new ArrayList<>();
        for(String line:Files.readAllLines(Paths.get(args[2]))){
            if(!line.contains("INFO"))continue;
            String raw=line.substring(line.indexOf('[')+1,line.indexOf('/')).replace('|',' ').trim();
            WordBuilder<String> w=new WordBuilder<>();for(String a:raw.split("\\s+")){if(!inputs.contains(a))throw new IllegalArgumentException("unknown PCE symbol "+a);w.append(a);}pces.add(w.toWord());
        }
        Oracle mq=new Oracle(target),eq=new Oracle(target);
        TTTLearnerMealy<String,String> learner=new TTTLearnerMealy<>(alphabet,mq,AcexAnalyzers.BINARY_SEARCH_BWD);
        CheckingEQOracle<MealyMachine<?,String,?,String>,String,Word<String>> candidates=new CheckingEQOracle<>(eq,1,pces);
        MealyWpMethodEQOracle<String,String> wp=new MealyWpMethodEQOracle<>(eq,Integer.parseInt(args[3]));
        long started=System.nanoTime();int rounds=1;learner.startLearning();
        MealyMachine<?,String,?,String> hypothesis;
        while(true){
            hypothesis=learner.getHypothesisModel();
            DefaultQuery<String,Word<String>> ce=candidates.findCounterExample(hypothesis,alphabet);
            if(ce==null)ce=wp.findCounterExample(hypothesis,alphabet);
            if(ce==null)break;
            if(rounds++>=100)throw new IllegalStateException("too many rounds");
            if(!learner.refineHypothesis(ce))throw new IllegalStateException("failed refinement");
        }
        try(PrintStream output=new PrintStream(args[4])){GraphDOT.write(hypothesis,alphabet,output);}
        double seconds=(System.nanoTime()-started)/1e9;
        System.out.printf(java.util.Locale.ROOT,"RESULT {\"mq\":%d,\"eq\":%d,\"mq_symbols\":%d,\"eq_symbols\":%d,\"rounds\":%d,\"states\":%d,\"seconds\":%.6f,\"pces\":%d}%n",mq.queries,eq.queries,mq.symbols,eq.symbols,rounds,hypothesis.size(),seconds,pces.size());
    }
}
