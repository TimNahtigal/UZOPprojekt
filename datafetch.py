from dataclasses import dataclass
import pandas as pd
import numpy as np
import sqlite3
import datetime as dt
import copy
import json
import pickle
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances_argmin_min 
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.multiclass import OneVsRestClassifier
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.preprocessing import normalize

from sklearn.metrics import silhouette_score

# Support functions
def getDictOfRegions():
    df = pd.read_csv('final_data/regijeid.csv')
    region_dict = dict(zip(df['region_name'], df['region_id']))
    return region_dict

@dataclass # Implementira equals avtomatično
class NoviceParametri:
    start_time : dt.datetime | None = None
    end_time : dt.datetime | None = None 
    regions : set[str] = None


class DataBroker:
    cached_parameters : NoviceParametri = NoviceParametri()
    cached_data :  pd.DataFrame | None = None 
    
    db_connection : sqlite3.Connection = None
    dict_of_regions : dict[str, str] = None
    loaded_vocab : np.ndarray[str] = None

    random_seed = None

    _logger = None
    
    def clearAllCache(self):
        self.cached_parameters = None
        self.cached_data = None
        self.cached_data_by_topic = None
        self.cached_topic = None

    def __init__(self, dbConnection : sqlite3.Connection, random_seed = None, logger = None):
        self.db_connection = dbConnection
        self.dict_of_regions = getDictOfRegions()
        self.loaded_vocab = np.load('./final_data/tfidf_vocab.npy', allow_pickle=True)
        self.random_seed = random_seed
        if logger is None:
            self._logger = print
        else:
            self._logger = logger
    
    def getData(self) -> pd.DataFrame:
        return self.cached_data

    def pridobiNovice(self, params: NoviceParametri | None = None) -> pd.DataFrame:
        """
        Dobi in kašira novice, ki zadostujejo nekim parametrom ( start date, end date, regions list (id format ali pa ime) ). 
        """
        # Če so parametri kaširani in data ni none
        if params == self.cached_parameters and self.cached_data is not None:
            self._logger("I have cached the news!")
            return self.cached_data
        
        self.clearAllCache()
        
        if params is None:
            params = NoviceParametri() # Brez parametrov

        remaped_params = copy.deepcopy(params)

        # FIX: Safely extract names from list structures if nested to avoid unhashable type list error
        if remaped_params.regions and not all(isinstance(r, str) and len(r) == 5 for r in params.regions):
            flat_regions = []
            for r in remaped_params.regions:
                if isinstance(r, list):
                    flat_regions.extend(r)
                else:
                    flat_regions.append(r)
                    
            remaped_params.regions = {
                self.dict_of_regions[name] 
                for name in flat_regions 
                if name in self.dict_of_regions
            }
            

        # UPDATED SQL: Added a JOIN to the regije table in the subquery to fetch r_nas.name 
        query = """
        SELECT 
            n.id, 
            n.title,
            n.content, 
            n.clean_content,
            n.topic, 
            n.date, 
            n.tfidf,
            (
                SELECT '[' || GROUP_CONCAT('["' || r_sub.id || '", "' || r_sub.name || '"]') || ']'
                FROM novice_regije nr_sub
                JOIN regije r_sub ON nr_sub.regija_id = r_sub.id
                WHERE nr_sub.novica_id = n.id
            ) AS regions,
            (
                SELECT '[' || GROUP_CONCAT('["' || nn.regija_id || '", "' || r_nas.name || '", "' || nn.naselje || '"]') || ']' 
                FROM novice_naselja nn
                JOIN regije r_nas ON nn.regija_id = r_nas.id
                WHERE nn.novica_id = n.id
            ) AS intersected_naselja
        FROM novice n
        WHERE 1=1
        """
        
        args = []
        
        if remaped_params.start_time:
            query += " AND n.date >= ?"
            args.append(remaped_params.start_time.date())
            
        if remaped_params.end_time:
            query += " AND n.date <= ?"
            args.append(remaped_params.end_time.date())
            
        # Keep filtration functional by joining against the target criteria table
        if remaped_params.regions:
            placeholders = ', '.join(['?'] * len(remaped_params.regions))
            query += f""" AND n.id IN (
                SELECT novica_id FROM novice_regije WHERE regija_id IN ({placeholders})
            )"""
            args.extend(list(remaped_params.regions))
            
        df = pd.read_sql_query(query, self.db_connection, params=args)
        
        def parse_regions(x):
            if not x:
                return []
            try:
                return [tuple(item) for item in json.loads(x)]
            except Exception:
                return []
        df['regions'] = df['regions'].apply(parse_regions)
        
        # Handle tfidf unpickling (since we switched to pickle in save function)
        def load_tfidf(x):
            if not x: return None
            try:
                return pickle.loads(x)
            except Exception:
                return np.frombuffer(x, dtype=np.float64) # fallback to your old variant
        df['tfidf'] = df['tfidf'].apply(load_tfidf)
        
        # New transformation: Safely builds 3-element tuples (id, region name, naselje)
        def parse_naselja(x):
            if not x: 
                return []
            try:
                return [tuple(item) for item in json.loads(x)]
            except Exception:
                return []
                
        df['intersected_naselja'] = df['intersected_naselja'].apply(parse_naselja)
        
        # Keep original exact sorting structure intact
        self.cached_data = df.sort_index()
        self.cached_parameters = copy.deepcopy(params)

        return self.cached_data

    
    def getPomembnostTopicov(self, novice_df : pd.DataFrame = None) -> pd.DataFrame:
        '''
            Pridobi pomembnosti topic (prešteje) za dataframe
        '''
        if novice_df is None:
            if self.cached_data is None:
                self.pridobiNovice()

            return self.cached_data['topic'].value_counts()
        else:
            return novice_df['topic'].value_counts()

    def topNnovicIzTopica(self, topics: str | set[str] | None = None, st_gruc: int = 3, st_clankov_na_gruco: int = 3, pridobi_pomembnosti_besed: bool = False, regression: str | None = None):
        """
        Pridobi top novice iz podnega topica. 
        Topici so lahko podani kot string ali set.
        Št. novic je enak št. končnih clusterjev. 
        Pridobi pomembnost besed ti poda besede po pomenbnosti, ampak to traja čas
        Regression: 
            - None       vzame sredino clusterja
            - logreg     regresija
            - logregcv   regresija z prečnim preverjanjem

        vrne touple:
        (
            novice,
            pomembnosti besed dict, kjer so ključi cluster id. in value seznam (beseda, pomembnost),
            št. novic v clusterju
        )
        """
        if self.cached_data is None:
            self._logger("Novice še niso pridobljene! Pridobil jih bom sam")
            self.pridobiNovice()

        if topics is None:
            topics = set()

        if not isinstance(topics, set):
            topics = set([topics])

        if topics == set():
            data_in_topic = self.cached_data
        else:
            data_in_topic = self.cached_data[self.cached_data["topic"].isin(topics)]

        self._logger("Started")
        
        # Parse text arrays
        tfidf_data = np.stack(data_in_topic["tfidf"].values)
        n_novic_v_topicu = len(data_in_topic)

        # --- Handle Single Cluster Edge Case Condition ---
        is_single_cluster = (st_gruc == 1) or (n_novic_v_topicu <= 1)

        if is_single_cluster:
            self._logger(f"Using a single cluster approach (Total articles: {n_novic_v_topicu})")
            # If grouping is forced to 1, all elements belong to a unified block
            st_gruc = 1 
            data_in_topic["cluster_label"] = 0
            # Centroid is simply the mathematical average of all features combined
            centroidi = np.mean(tfidf_data, axis=0, keepdims=True)
            
            if regression not in [None, "clustercenter"]:
                self._logger(f"[WARNING: Regression '{regression}' requires at least 2 unique classes. Falling back to 'clustercenter'.]")
                regression = "clustercenter"
        else:
            # Standard Multi-Cluster Workflow
            kmeans = KMeans(n_clusters=st_gruc, random_state=self.random_seed, init='k-means++', n_init=20)
            data_in_topic["cluster_label"] = kmeans.fit_predict(tfidf_data)
            centroidi = kmeans.cluster_centers_
            self._logger("Made clusters")

        # --- Cluster Quality Score Check ---
        cluster_score = None
        edinstvene_gruce = len(set(data_in_topic["cluster_label"]))

        if is_single_cluster or edinstvene_gruce <= 1:
            self._logger("[WARNING: Cluster quality score not available. Reason: Single cluster scenario.]")
        elif n_novic_v_topicu <= st_gruc:
            self._logger("[WARNING: Cluster quality score not available. Reason: Too few articles for requested groups.]")
        else:
            try:
                cluster_score = silhouette_score(
                    tfidf_data, 
                    data_in_topic["cluster_label"],
                    metric="cosine"
                )
                self._logger(f"Cluster quality score (silhouette): [{cluster_score:.3f}]")
            except Exception as e:
                self._logger(f"[WARNING: Cluster quality score not available. Math/Data error: {e}]")

        # Find closest items to centers
        rows = []
        for cluster_id in range(st_gruc):
            cluster_mask = data_in_topic["cluster_label"] == cluster_id
            cluster_df = data_in_topic[cluster_mask].copy()

            if cluster_df.empty:
                continue

            cluster_vectors = np.stack(cluster_df["tfidf"].values)
            centroid = centroidi[cluster_id].reshape(1, -1)

            _, distances = pairwise_distances_argmin_min(cluster_vectors, centroid)

            cluster_df["distance_to_centroid"] = distances
            cluster_df["cluster_size"] = len(cluster_df)

            rows.append(
                cluster_df.sort_values("distance_to_centroid")
                .head(st_clankov_na_gruco)
            )

        most_representative_news = pd.concat(rows)
        most_representative_news = most_representative_news.sort_values(
            by=["cluster_size", "cluster_label", "distance_to_centroid"],
            ascending=[False, True, True]
        )

        cluster_counts = data_in_topic['cluster_label'].value_counts()
        most_representative_news['cluster_size'] = most_representative_news['cluster_label'].map(cluster_counts)
        most_representative_news = most_representative_news.sort_values(by='cluster_size', ascending=False)

        self._logger("Sorted clusters")

        self._logger("\n--- Število novic po clusterjih ---")
        for cluster_id, count in cluster_counts.items():
            self._logger(f"Cluster {cluster_id}: [{count}] novic")
        self._logger("-"*25)

        if not pridobi_pomembnosti_besed:
            return (most_representative_news, None, cluster_score)
        
        # --- Handle auto-reg mode logging configuration changes ---
        if regression == "auto-reg":
            if is_single_cluster:
                regression = "clustercenter"
                self._logger("Auto-reg selection: Single cluster evaluated -> Selected 'clustercenter'")
            else:
                n_novic = len(data_in_topic)
                if n_novic < 30:
                    regression = "logregcv"
                    self._logger(f"Auto-reg selection: {n_novic} novic -> Selected 'logregcv'")
                elif n_novic < 200:
                    regression = "logreg"
                    self._logger(f"Auto-reg selection: {n_novic} novic -> Selected 'logreg' with predefined C")
                else:
                    regression = "logreg_sampled"
                    self._logger(f"Auto-reg selection: {n_novic} novic -> Selected 'logreg_sampled' on random sample")

        if regression == "clustercenter" or regression is None:
            if regression is None:
                self._logger("Not using regression (defaulting to clustercenter weights)")
                regression = "clustercenter"
                
            importance_per_cluster = {}
            vocab_array = np.array(self.loaded_vocab)

            for cluster_id in range(len(centroidi)):
                scores = centroidi[cluster_id]
                
                total_cluster_sum = np.sum(scores)
                if total_cluster_sum > 0:
                    norm_scores = scores / total_cluster_sum
                    relevant_indices = np.where(norm_scores > 0.01)[0]
                    sorted_indices = relevant_indices[np.argsort(norm_scores[relevant_indices])[::-1]]
                    
                    importance_per_cluster[cluster_id] = [
                        (vocab_array[idx], norm_scores[idx]) 
                        for idx in sorted_indices
                    ]
                else:
                    importance_per_cluster[cluster_id] = []
        else:
            # --- Standard Multi-Class Regression Processing Layer ---
            clf = None
            if regression == "logregcv":
                try:
                    clf = LogisticRegressionCV(
                        solver='saga', 
                        penalty='l1', 
                        max_iter=2000,
                        class_weight='balanced',
                        n_jobs=-1
                    ).fit(tfidf_data, data_in_topic['cluster_label'])
                except Exception as e:
                    self._logger(f"[WARNING: LogisticRegressionCV stratified validation split failed: {e}. Falling back to 'logreg'.]")
                    regression = "logreg"

            if regression == "logreg":
                clf = LogisticRegression(
                    solver='saga', 
                    penalty='l1', 
                    max_iter=2000,
                    C=5,
                    class_weight='balanced',
                    n_jobs=-1
                ).fit(tfidf_data, data_in_topic['cluster_label'])

            elif regression == "logreg_sampled":
                sample_size = min(200, len(data_in_topic))
                sampled_data = data_in_topic.sample(n=sample_size, random_state=self.random_seed)

                tfidf_sample = np.stack(sampled_data["tfidf"].values)
                labels_sample = sampled_data["cluster_label"]
                clf = LogisticRegression(
                    solver='saga',
                    penalty='l1',
                    max_iter=2000,
                    C=5,
                    class_weight='balanced',
                    n_jobs=-1
                ).fit(tfidf_sample, labels_sample)

            if clf is None:
                self._logger("Izberi regresijo!")
                return None       
            
            importance_per_cluster = {}
            vocab_array = np.array(self.loaded_vocab, dtype=str)

            if clf.coef_.shape[0] == 1:
                coef_matrix = np.vstack([-clf.coef_, clf.coef_])
            else:
                coef_matrix = clf.coef_

            for i, cluster_id in enumerate(clf.classes_): 
                coefs = coef_matrix[i]
                abs_coefs = np.abs(coefs)
                total_magnitude = np.sum(abs_coefs)
                
                if total_magnitude > 0:
                    norm_importance = abs_coefs / total_magnitude 
                    relevant_indices = np.where(norm_importance > 0.01)[0]
                    sorted_indices = relevant_indices[np.argsort(norm_importance[relevant_indices])[::-1]]
                    
                    importance_per_cluster[cluster_id] = [
                        (vocab_array[idx], norm_importance[idx]) 
                        for idx in sorted_indices
                    ]
                else:
                    importance_per_cluster[cluster_id] = []

        # Display results
        for cluster_id, features in importance_per_cluster.items():
            top_5_features = features[:5]
            self._logger(f"Cluster {cluster_id} ([Atribute importance]/cluster center importance):")
            
            for word, importance_score in top_5_features:
                try:
                    if regression == "clustercenter":
                        cc_value = importance_score
                    else:
                        indices = np.where(vocab_array == str(word))[0]
                        if indices.size > 0:
                            word_idx = indices[0]
                            raw_scores = centroidi[cluster_id]
                            total_cluster_sum = np.sum(raw_scores)
                            
                            if total_cluster_sum > 0:
                                cc_value = raw_scores[word_idx] / total_cluster_sum
                            else:
                                cc_value = 0.0
                        else:
                            cc_value = 0.0
                except (ValueError, IndexError):
                    cc_value = 0.0

                self._logger(f"[{word} {importance_score:.3f}]/{cc_value:.3f}")

        return (most_representative_news, importance_per_cluster, cluster_score)        

    def chooseOptimalnoSteviloGruc(self, topics=None, min_k=2, max_k=10):
        if self.cached_data is None:
            self.pridobiNovice()

        if topics is None:
            topics = set()

        if not isinstance(topics, set):
            topics = set([topics])

        if topics == set():
            data_in_topic = self.cached_data
        else:
            data_in_topic = self.cached_data[self.cached_data["topic"].isin(topics)]

        if len(data_in_topic) <= min_k:
            return len(data_in_topic), None

        tfidf_data = np.stack(data_in_topic["tfidf"].values)

        max_k = min(max_k, len(data_in_topic) - 1)
        best_k = min_k
        best_score = -1

        for k in range(min_k, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=self.random_seed, 
                        init="k-means++", n_init=10)
            labels = kmeans.fit_predict(tfidf_data)
            score = silhouette_score(tfidf_data, labels, metric="euclidean") #zato ker tf-idf uporablja evklidsko
            
            self._logger(f"K={k}, Silhouette Score: {score:.4f}")
            
            if score > best_score:
                best_score = score
                best_k = k

        return best_k, best_score

if __name__ == "__main__":
    connection = sqlite3.connect('final_data/novice.db') # Naredi db če še ne obstaja
    connection.execute("PRAGMA foreign_keys = ON")
    broker = DataBroker(connection)

    testParam = NoviceParametri(regions={"Gorenjska"})
    #testParam = NoviceParametri()
    #print(broker.pridobiNovice(testParam))

    #broker.topNnovicIzTopica(pridobi_pomembnosti_besed=True, regression="logreg")
    broker.topNnovicIzTopica(pridobi_pomembnosti_besed=True, regression=None)
    print(broker.getData())



