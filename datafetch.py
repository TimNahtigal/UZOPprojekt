from dataclasses import dataclass
import pandas as pd
import numpy as np
import sqlite3
import datetime as dt
import copy

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances_argmin_min 
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.multiclass import OneVsRestClassifier
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
# Support functions
def getDictOfRegions():
    df = pd.read_csv('final_data/regijeid.csv')
    region_dict = dict(zip(df['region_name'], df['region_id']))
    return region_dict

@dataclass # Implementira equals avtomatično
class NoviceParametri:
    start_time : dt.datetime | None = None
    end_time : dt.datetime | None = None 
    regions : set[str] | None = None


class DataBroker:
    cached_parameters : NoviceParametri = NoviceParametri()
    cached_data :  pd.DataFrame | None = None 
    
    db_connection : sqlite3.Connection = None
    dict_of_regions : dict[str, str] = None
    loaded_vocab : np.ndarray[str] = None

    random_seed = None

    _logger = None
    
    def clearAllCache(self):
        cached_parameters = None
        cached_data = None
        cached_data_by_topic = None
        cached_topic = None

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
        self.clearAllCache()

        # Če so parametri kaširani in data ni none
        if params == self.cached_parameters and self.cached_data is not None:
            return self.cached_data
        
        if params is None:
            params = NoviceParametri() # Brez parametrov

        # Remapi regije v id format
        if params.regions and not all(len(r) == 5 for r in params.regions): # Če so slučajno že v id formatu
            params.regions = {
                self.dict_of_regions[name] 
                for name in params.regions 
                if name in self.dict_of_regions
            }
            
        remaped_params = copy.copy(params)

        query = """
        SELECT 
            n.id, 
            n.content, 
            n.clean_content,
            n.topic, 
            n.date, 
            GROUP_CONCAT(r.name, ', ') AS regions,
            n.tfidf
        FROM novice n
        JOIN novice_regije nr ON n.id = nr.novica_id
        JOIN regije r ON nr.regija_id = r.id
        WHERE 1=1
        """
        
        args = []
        
        if remaped_params.start_time:
            query += " AND n.date >= ?"
            args.append(remaped_params.start_time.date())
            
        if remaped_params.end_time:
            query += " AND n.date <= ?"
            args.append(remaped_params.end_time.date())
            
        if remaped_params.regions:
            placeholders = ', '.join(['?'] * len(remaped_params.regions))
            query += f" AND r.id IN ({placeholders})"
            args.extend(list(remaped_params.regions))

        query += " GROUP BY n.id"
        
        df = pd.read_sql_query(query, self.db_connection, params=args)
        
        df['regions'] = df['regions'].apply(lambda x: x.split(', ') if x else [])
        df['tfidf'] = df['tfidf'].apply(lambda x: np.frombuffer(x, dtype=np.float64) if x else None)
        self.cached_data = df.sort_index()
        self.cached_parameters = remaped_params
    
    def getPomembnostTopicov(self, novice_df : pd.DataFrame) -> pd.DataFrame:
        '''
            Pridobi pomembnosti topic (prešteje) za dataframe
        '''
        if self.cached_data is None:
            self.pridobiNovice()

        return self.cached_data['topic'].value_counts()

    def topNnovicIzTopica(self, topics: str | set[str] | None = None, st_novic : int = 3, pridobi_pomembnosti_besed : bool = False, regression : str | None = None):
        """
        Pridobi top novice iz podnega topica. 
        Topici so lahko podani kot string ali set.
        Št. novic je enak št. končnih clusterjev. 
        Pridobi pomembnost besed ti poda besede po pomenbnosti, ampak to traja čas
        Regression: 
            - None       vzame sredino clusterja
            - logreg     regresija
            - logregcv   regresija z prečnim preverjanjem
        """
        if self.cached_data == None:
            self._logger("Novice še niso pridobljene! Pridobil jih bom sam")
            self.pridobiNovice()

        if topics is None:
            topics = set()

        if not isinstance(topics, set):
            topics = set(topics)

        if topics == set():
            data_in_topic = self.cached_data
        else:
            data_in_topic = self.cached_data[self.cached_data["topic"].isin(topics)]

        self._logger("Started")
        
        # Naredi clusterje
        tfidf_data = np.stack(data_in_topic["tfidf"].values)
        kmeans = KMeans(n_clusters=st_novic, random_state=self.random_seed, init='k-means++', n_init=20)
        data_in_topic["cluster_label"] = kmeans.fit_predict(tfidf_data)
        
        self._logger("Made clusters")

        # Najde sredine clusterjev
        centroidi = kmeans.cluster_centers_
        closest_indices, _ = pairwise_distances_argmin_min(centroidi, tfidf_data)
        most_representative_news = data_in_topic.iloc[closest_indices]
        #self._logger(most_representative_news)
        self._logger("Found cluster centers")

        # Sortiraj po najbolj pomembnem clusterju (najbolj pomemben cluster je tist z največ novic)
        cluster_counts = data_in_topic['cluster_label'].value_counts()
        most_representative_news['cluster_size'] = most_representative_news['cluster_label'].map(cluster_counts)
        most_representative_news = most_representative_news.sort_values(by='cluster_size', ascending=False)

        self._logger("Sorted clusters")

        self._logger("\n--- Število novic po clusterjih ---")
        for cluster_id, count in cluster_counts.items():
            self._logger(f"Cluster {cluster_id}: {count} novic")
        self._logger("-----------------------------------\n")

        # coords = TSNE(n_components=2, perplexity=30, random_state=42).fit_transform(tfidf_data)
        # plt.figure(figsize=(10, 7))
        # scatter = plt.scatter(coords[:, 0], coords[:, 1], c=data_in_topic["cluster_label"], cmap='viridis', alpha=0.6)
        # plt.colorbar(scatter, label='Cluster ID')
        # plt.title(f'Vizualizacija {st_novic} clusterjev (PCA redukcija)')
        # plt.xlabel('Glavna komponenta 1')
        # plt.ylabel('Glavna komponenta 2')
        # rep_coords = coords[closest_indices]
        # plt.scatter(rep_coords[:, 0], rep_coords[:, 1], c='red', marker='X', s=100, label='Središča (Centroidi)')
        # plt.legend()
        # plt.show()

        if not pridobi_pomembnosti_besed:
            # Če rabimo samo najbolj representetive news, ne pa pomembnosti besed
            return most_representative_news
        
        if regression is None:
            self._logger("Not using regression")
            centroidi = kmeans.cluster_centers_

            importance_per_cluster = {}
            vocab_array = np.array(self.loaded_vocab)

            for cluster_id in range(len(centroidi)):
                scores = centroidi[cluster_id]
                
                top_indices = np.argpartition(scores, -10)[-10:] # TOP 10
                
                top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

                raw_results = [
                    (vocab_array[idx], scores[idx]) 
                    for idx in top_indices if scores[idx] > 0
                ]
                
                if raw_results:
                    total_score = sum(weight for word, weight in raw_results)
                    
                    importance_per_cluster[cluster_id] = [
                        (word, weight / total_score) for word, weight in raw_results
                    ]
                else:
                    importance_per_cluster[cluster_id] = []
        else:
            if regression == "logregcv":
                clf = LogisticRegressionCV(
                    solver='saga', 
                    penalty='l1', 
                    max_iter=2000,
                    class_weight='balanced',
                    n_jobs=-1
                ).fit(tfidf_data, data_in_topic['cluster_label'])
            elif regression == "logreg": # Najhitrejši somehow (mby celo najboljši)
                clf = LogisticRegression(
                    solver='saga', 
                    penalty='l1', 
                    max_iter=2000,
                    C=5,
                    class_weight='balanced', # Da nima največji cluster ogromno besed, ki so common vsem
                    n_jobs=-1 # Multithreading
                ).fit(tfidf_data, data_in_topic['cluster_label'])
            else:
                self._logger("Izberi regresijo!")
                return None
            
            importance_per_cluster = {}
            for i, cluster_id in enumerate(clf.classes_): 
                coefs = clf.coef_[i]
                
                top_indices = np.argsort(np.abs(coefs))[::-1][:10] # TOP 10

                raw_results = [
                    (self.loaded_vocab[idx], abs(coefs[idx])) 
                    for idx in top_indices if coefs[idx] != 0
                ]
                
                if raw_results:
                        total_abs_score = sum(weight for _, weight in raw_results)
                        
                        importance_per_cluster[cluster_id] = [
                            (word, weight / total_abs_score) for word, weight in raw_results
                        ]
                else:
                    importance_per_cluster[cluster_id] = []


        # Display results
        for cluster, features in importance_per_cluster.items():
            self._logger(f"Cluster {cluster} Top Attributes: {features}")

        cluster_counts = data_in_topic['cluster_label'].value_counts().sort_index()

if __name__ == "__main__":
    connection = sqlite3.connect('final_data/novice.db') # Naredi db če še ne obstaja
    connection.execute("PRAGMA foreign_keys = ON")
    broker = DataBroker(connection)

    testParam = NoviceParametri(regions={"Gorenjska"})
    #testParam = NoviceParametri()

    #broker.topNnovicIzTopica(pridobi_pomembnosti_besed=True, regression="logreg")
    broker.topNnovicIzTopica(pridobi_pomembnosti_besed=True, regression=None)




